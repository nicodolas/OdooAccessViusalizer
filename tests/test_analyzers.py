from types import SimpleNamespace

from odoo.tests.common import TransactionCase

from ..services.analyzers import acl, implied_groups, record_rules


class FakeMany2Many:
    def __init__(self, ids):
        self.ids = list(ids)


class FakeRecord:
    def __init__(self, record_id, name, implied=None, module="test", groups=None):
        self.id = record_id
        self.name = name
        self.display_name = name
        self._name = "res.groups"
        self.implied_ids = FakeMany2Many(implied or [])
        self.groups = FakeMany2Many(groups or [])
        self.module = module


class FakeGroupSet(list):
    def filtered(self, predicate):
        return FakeGroupSet(record for record in self if predicate(record))


class FakeNormalizer:
    def module_for(self, model, record_id):
        return next(record.module for record in self.groups if record.id == record_id)

    def key(self, node_type, model, record_id):
        return f"{node_type}:{model}:{record_id}"

    def __init__(self, groups):
        self.groups = groups


class ImpliedGroupAnalyzerTest(TransactionCase):
    def test_transitive_closure(self):
        groups = FakeGroupSet(
            [
                FakeRecord(1, "Manager", implied=[2]),
                FakeRecord(2, "User", implied=[3]),
                FakeRecord(3, "Employee"),
            ]
        )
        closure = implied_groups.transitive_closure(groups)
        self.assertEqual(closure[1], {2, 3})
        self.assertEqual(closure[2], {3})

    def test_cross_module_overlap_is_reported(self):
        groups = FakeGroupSet(
            [
                FakeRecord(1, "Sales", implied=[3], module="sale"),
                FakeRecord(2, "HR", implied=[3], module="hr"),
                FakeRecord(3, "Base", module="base"),
            ]
        )
        findings = implied_groups.analyze(groups, FakeNormalizer(groups))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["finding_type"], "implied_overlap")
        self.assertEqual(findings[0]["certainty"], "deterministic")


class RuleAnalyzerTest(TransactionCase):
    def test_domain_fields_are_extracted_without_evaluation(self):
        fields = record_rules.extract_domain_fields(
            "[('company_id', '=', user.company_id.id), ('state', 'in', company_ids)]"
        )
        self.assertEqual(fields, {"company_id", "state"})


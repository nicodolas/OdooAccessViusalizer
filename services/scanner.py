import logging

from .analyzers import acl, implied_groups, record_rules
from .normalizer import AccessSnapshotNormalizer

_logger = logging.getLogger(__name__)


class AccessSnapshotScanner:
    def __init__(self, env, snapshot):
        self.env = env
        self.snapshot = snapshot
        self.normalizer = AccessSnapshotNormalizer(env)

    def _read_sources(self):
        sources = {
            "users": self.env["res.users"].sudo().search([]),
            "groups": self.env["res.groups"].sudo().search([]),
            "privileges": self.env["res.groups.privilege"].sudo().search([]),
            "models": self.env["ir.model"].sudo().search([]),
            "access": self.env["ir.model.access"].sudo().search([]),
            "rules": self.env["ir.rule"].sudo().search([]),
            "menus": self.env["ir.ui.menu"].sudo().search([]),
        }
        for model_name, records in (
            ("res.users", sources["users"]),
            ("res.groups", sources["groups"]),
            ("res.groups.privilege", sources["privileges"]),
            ("ir.model", sources["models"]),
            ("ir.model.access", sources["access"]),
            ("ir.rule", sources["rules"]),
            ("ir.ui.menu", sources["menus"]),
        ):
            self.normalizer.load_provenance(model_name, records.ids)
        return sources

    def _build_graph(self, sources):
        normalizer = self.normalizer
        categories = self.env["ir.module.category"].sudo().search([])
        normalizer.load_provenance("ir.module.category", categories.ids)

        category_keys = {}
        for category in categories:
            category_keys[category.id] = normalizer.add_node(
                "category", category, label=category.name, metadata={"sequence": category.sequence}
            )

        privilege_keys = {}
        for privilege in sources["privileges"]:
            key = normalizer.add_node(
                "privilege",
                privilege,
                label=privilege.name,
                metadata={"description": privilege.description or "", "sequence": privilege.sequence},
            )
            privilege_keys[privilege.id] = key
            if privilege.category_id:
                category_key = category_keys.get(privilege.category_id.id)
                if category_key:
                    normalizer.add_edge(category_key, key, "contains")

        group_keys = {}
        for group in sources["groups"]:
            privilege = group.privilege_id
            group_keys[group.id] = normalizer.add_node(
                "group",
                group,
                label=group.display_name,
                technical_name=group.name,
                module=normalizer.module_for(group._name, group.id),
                category=privilege.category_id.name if privilege and privilege.category_id else False,
                metadata={
                    "user_count": group.all_users_count,
                    "privilege_id": privilege.id if privilege else False,
                    "active": True,
                },
            )
            if privilege and privilege.id in privilege_keys:
                normalizer.add_edge(privilege_keys[privilege.id], group_keys[group.id], "contains")

        for group in sources["groups"]:
            for implied in group.implied_ids:
                if implied.id in group_keys:
                    normalizer.add_edge(group_keys[group.id], group_keys[implied.id], "implied")

        for user in sources["users"]:
            user_key = normalizer.add_node(
                "user",
                user,
                label=user.display_name,
                technical_name=user.login,
                metadata={"active": user.active, "share": user.share},
            )
            for group in user.group_ids:
                if group.id in group_keys:
                    normalizer.add_edge(user_key, group_keys[group.id], "membership")

        model_keys = {}
        for model in sources["models"]:
            model_keys[model.id] = normalizer.add_node(
                "model",
                model,
                label=model.name,
                technical_name=model.model,
                metadata={"transient": model.transient, "abstract": model.abstract},
            )

        for access in sources["access"]:
            acl_key = normalizer.add_node(
                "acl",
                access,
                label=access.name,
                metadata={
                    "active": access.active,
                    "group_id": access.group_id.id if access.group_id else False,
                    "model_id": access.model_id.id if access.model_id else False,
                    "perm_read": access.perm_read,
                    "perm_write": access.perm_write,
                    "perm_create": access.perm_create,
                    "perm_unlink": access.perm_unlink,
                },
            )
            if access.group_id and access.group_id.id in group_keys:
                normalizer.add_edge(group_keys[access.group_id.id], acl_key, "grants")
            if access.model_id and access.model_id.id in model_keys:
                normalizer.add_edge(acl_key, model_keys[access.model_id.id], "protects")

        for rule in sources["rules"]:
            rule_key = normalizer.add_node(
                "rule",
                rule,
                label=rule.name or f"Rule {rule.id}",
                metadata={
                    "active": rule.active,
                    "global": not bool(rule.groups),
                    "domain_force": rule.domain_force or "[]",
                    "perm_read": rule.perm_read,
                    "perm_write": rule.perm_write,
                    "perm_create": rule.perm_create,
                    "perm_unlink": rule.perm_unlink,
                },
            )
            for group in rule.groups:
                if group.id in group_keys:
                    normalizer.add_edge(group_keys[group.id], rule_key, "applies")
            if rule.model_id and rule.model_id.id in model_keys:
                normalizer.add_edge(rule_key, model_keys[rule.model_id.id], "protects")

        for menu in sources["menus"]:
            menu_key = normalizer.add_node(
                "menu",
                menu,
                label=menu.complete_name or menu.name,
                technical_name=menu.name,
                metadata={"active": menu.active, "action": str(menu.action or "")},
            )
            for group in menu.group_ids:
                if group.id in group_keys:
                    normalizer.add_edge(group_keys[group.id], menu_key, "shows")

    def _write_batches(self, model, values, batch_size=500):
        for offset in range(0, len(values), batch_size):
            model.create(values[offset : offset + batch_size])

    def run(self):
        sources = self._read_sources()
        self._build_graph(sources)
        findings = []
        findings.extend(implied_groups.analyze(sources["groups"], self.normalizer))
        findings.extend(acl.analyze(sources["access"], sources["groups"], self.normalizer))
        findings.extend(record_rules.analyze(sources["rules"], self.normalizer))

        Node = self.env["oav.access.snapshot.node"].sudo()
        Edge = self.env["oav.access.snapshot.edge"].sudo()
        Finding = self.env["oav.access.finding"].sudo()
        node_values = [dict(values, snapshot_id=self.snapshot.id) for values in self.normalizer.nodes.values()]
        edge_values = [dict(values, snapshot_id=self.snapshot.id) for values in self.normalizer.edges.values()]
        finding_values = [dict(value, snapshot_id=self.snapshot.id) for value in findings]
        self._write_batches(Node, node_values)
        self._write_batches(Edge, edge_values)
        self._write_batches(Finding, finding_values)
        return {
            "node_count": len(node_values),
            "edge_count": len(edge_values),
            "finding_count": len(finding_values),
        }


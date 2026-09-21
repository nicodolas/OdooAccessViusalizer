from collections import defaultdict

from .base import FindingBuilder
from .implied_groups import transitive_closure


def _rights(access):
    return {
        mode
        for mode, enabled in (
            ("read", access.perm_read),
            ("write", access.perm_write),
            ("create", access.perm_create),
            ("unlink", access.perm_unlink),
        )
        if enabled
    }


def analyze(access_records, groups, normalizer):
    builder = FindingBuilder()
    active = access_records.filtered(lambda access: access.active)
    by_model = defaultdict(list)
    for access in active:
        by_model[access.model_id.id].append(access)

    closure = transitive_closure(groups)
    for model_id, records in by_model.items():
        model_name = records[0].model_id.model if records else False
        if len(records) >= 3 and len({record.group_id.id for record in records}) >= 2:
            builder.add(
                "acl_complexity",
                "warning",
                "deterministic",
                "Complex ACL landscape",
                f"{len(records)} active ACL rows apply to {model_name}.",
                "Review the effective CRUD union and remove rows that are no longer needed.",
                model_name=model_name,
                evidence={
                    "acl_count": len(records),
                    "group_count": len({record.group_id.id for record in records}),
                },
                node_keys=[
                    normalizer.key("acl", record._name, record.id) for record in records
                ],
            )

        seen_signatures = {}
        for access in records:
            signature = (
                access.model_id.id,
                access.group_id.id or 0,
                tuple(sorted(_rights(access))),
            )
            if signature in seen_signatures:
                previous = seen_signatures[signature]
                builder.add(
                    "acl_redundancy",
                    "warning",
                    "deterministic",
                    "Duplicate access control",
                    f"ACL {access.name} duplicates {previous.name} for {model_name}.",
                    "Keep one active ACL row and remove the duplicate through Odoo security settings.",
                    model_name=model_name,
                    evidence={"duplicate_acl_ids": [previous.id, access.id], "rights": sorted(_rights(access))},
                    node_keys=[
                        normalizer.key("acl", previous._name, previous.id),
                        normalizer.key("acl", access._name, access.id),
                    ],
                )
            else:
                seen_signatures[signature] = access

        for access in records:
            if not access.group_id:
                continue
            access_rights = _rights(access)
            for other in records:
                if access == other or not other.group_id:
                    continue
                other_rights = _rights(other)
                if other.group_id.id in closure.get(access.group_id.id, set()) and access_rights <= other_rights:
                    builder.add(
                        "acl_redundancy",
                        "warning",
                        "deterministic",
                        "Inherited ACL may be redundant",
                        (
                            f"ACL {access.name} on {model_name} is a subset of ACL {other.name}; "
                            f"{access.group_id.display_name} implies {other.group_id.display_name}."
                        ),
                        "Confirm the narrower ACL is not needed for documentation or future group changes.",
                        model_name=model_name,
                        evidence={
                            "subset_acl_id": access.id,
                            "implying_acl_id": other.id,
                            "subset_rights": sorted(access_rights),
                            "superset_rights": sorted(other_rights),
                        },
                        node_keys=[
                            normalizer.key("acl", access._name, access.id),
                            normalizer.key("acl", other._name, other.id),
                            normalizer.key("group", access.group_id._name, access.group_id.id),
                            normalizer.key("group", other.group_id._name, other.group_id.id),
                        ],
                    )
    return builder.findings


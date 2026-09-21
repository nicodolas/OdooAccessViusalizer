from collections import defaultdict

from .base import FindingBuilder


def transitive_closure(groups):
    direct = {group.id: set(group.implied_ids.ids) for group in groups}
    closure = {}
    for group in groups:
        seen = set()
        pending = list(direct.get(group.id, set()))
        while pending:
            group_id = pending.pop()
            if group_id in seen or group_id == group.id:
                continue
            seen.add(group_id)
            pending.extend(direct.get(group_id, set()) - seen)
        closure[group.id] = seen
    return closure


def analyze(groups, normalizer):
    builder = FindingBuilder()
    closure = transitive_closure(groups)
    groups_by_implied = defaultdict(list)
    by_id = {group.id: group for group in groups}
    for group_id, implied_ids in closure.items():
        for implied_id in implied_ids:
            groups_by_implied[implied_id].append(group_id)

    for implied_id, group_ids in groups_by_implied.items():
        implied = by_id.get(implied_id)
        if not implied:
            continue
        groups_by_module = defaultdict(list)
        for group_id in group_ids:
            group = by_id[group_id]
            groups_by_module[normalizer.module_for(group._name, group.id)].append(group)
        if len(groups_by_module) < 2:
            continue
        node_keys = [normalizer.key("group", implied._name, implied.id)]
        module_summary = {}
        for module, module_groups in sorted(groups_by_module.items()):
            module_summary[module] = [group.display_name for group in module_groups]
            node_keys.extend(
                normalizer.key("group", group._name, group.id) for group in module_groups
            )
        builder.add(
            "implied_overlap",
            "warning",
            "deterministic",
            "Cross-module implied group overlap",
            (
                f"{sum(len(group_list) for group_list in groups_by_module.values())} groups "
                f"from {len(groups_by_module)} modules transitively imply {implied.display_name}."
            ),
            "Review whether the cross-module inheritance is intentional and documented.",
            evidence={
                "shared_implied_group": implied.display_name,
                "groups_by_module": module_summary,
                "module_count": len(groups_by_module),
            },
            node_keys=node_keys,
        )
    return builder.findings

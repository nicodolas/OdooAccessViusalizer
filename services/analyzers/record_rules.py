import re
from collections import defaultdict

from .base import FindingBuilder

DOMAIN_FIELD_RE = re.compile(
    r"['\"]([a-zA-Z_][a-zA-Z0-9_.]*)['\"]\s*,\s*['\"](?:=|!=|in|not in|like|ilike|not like|not ilike|child_of|parent_of)"
)


def extract_domain_fields(domain_text):
    return set(DOMAIN_FIELD_RE.findall(domain_text or ""))


def analyze(rules, normalizer):
    builder = FindingBuilder()
    active = rules.filtered(lambda rule: rule.active)
    by_model = defaultdict(list)
    for rule in active:
        by_model[rule.model_id.model].append(rule)

    for model_name, model_rules in by_model.items():
        signatures = {}
        global_rules = []
        group_rules = []
        for rule in model_rules:
            group_ids = tuple(sorted(rule.groups.ids))
            signature = (
                rule.domain_force or "",
                group_ids,
                rule.perm_read,
                rule.perm_write,
                rule.perm_create,
                rule.perm_unlink,
            )
            if signature in signatures:
                other = signatures[signature]
                builder.add(
                    "rule_duplicate",
                    "warning",
                    "deterministic",
                    "Duplicate record rule",
                    f"Rule {rule.name} duplicates {other.name} on {model_name}.",
                    "Keep one rule and document the intended access modes.",
                    model_name=model_name,
                    evidence={"rule_ids": [other.id, rule.id], "domain": rule.domain_force or "[]"},
                    node_keys=[
                        normalizer.key("rule", other._name, other.id),
                        normalizer.key("rule", rule._name, rule.id),
                    ],
                )
            else:
                signatures[signature] = rule
            (global_rules if not rule.groups else group_rules).append(rule)

        global_fields = {
            field
            for rule in global_rules
            for field in extract_domain_fields(rule.domain_force)
        }
        for rule in group_rules:
            overlap = global_fields.intersection(extract_domain_fields(rule.domain_force))
            if not overlap:
                continue
            node_keys = [normalizer.key("rule", rule._name, rule.id)] + [
                normalizer.key("rule", global_rule._name, global_rule.id)
                for global_rule in global_rules
                if overlap.intersection(extract_domain_fields(global_rule.domain_force))
            ]
            builder.add(
                "rule_potential_conflict",
                "warning",
                "heuristic",
                "Potential global/group rule interaction",
                (
                    f"A group rule on {model_name} shares domain field(s) {sorted(overlap)} "
                    "with one or more global rules."
                ),
                "Review the evaluated domain for representative users and companies; this finding is not a proof of contradiction.",
                model_name=model_name,
                evidence={
                    "overlapping_fields": sorted(overlap),
                    "group_rule_domain": rule.domain_force or "[]",
                    "global_rule_count": len(global_rules),
                },
                node_keys=node_keys,
            )
    return builder.findings


from odoo import fields, models


class AccessFinding(models.Model):
    _name = "oav.access.finding"
    _description = "Access Visualizer Finding"
    _order = "severity desc, certainty, finding_type, id"

    snapshot_id = fields.Many2one(
        "oav.access.snapshot", required=True, ondelete="cascade", index=True
    )
    finding_type = fields.Selection(
        [
            ("implied_overlap", "Implied Group Overlap"),
            ("acl_redundancy", "ACL Redundancy"),
            ("acl_complexity", "ACL Complexity"),
            ("rule_duplicate", "Duplicate Record Rule"),
            ("rule_potential_conflict", "Potential Record Rule Conflict"),
        ],
        required=True,
        index=True,
    )
    severity = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")],
        required=True,
        default="warning",
        index=True,
    )
    certainty = fields.Selection(
        [
            ("deterministic", "Deterministic"),
            ("heuristic", "Heuristic"),
            ("unknown", "Unknown"),
        ],
        required=True,
        default="heuristic",
        index=True,
    )
    title = fields.Char(required=True)
    description = fields.Text(required=True)
    recommendation = fields.Text()
    model_name = fields.Char(index=True)
    evidence_json = fields.Json(default=dict)
    affected_node_keys = fields.Json(default=list)
    affected_edge_keys = fields.Json(default=list)
    fingerprint = fields.Char(index=True)


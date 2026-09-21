from odoo import fields, models


class AccessSnapshotEdge(models.Model):
    _name = "oav.access.snapshot.edge"
    _description = "Access Visualizer Snapshot Edge"
    _order = "edge_type, id"

    snapshot_id = fields.Many2one(
        "oav.access.snapshot", required=True, ondelete="cascade", index=True
    )
    source_key = fields.Char(required=True, index=True)
    target_key = fields.Char(required=True, index=True)
    edge_type = fields.Selection(
        [
            ("membership", "User Membership"),
            ("implied", "Implied Group"),
            ("contains", "Contains"),
            ("grants", "Grants Access"),
            ("protects", "Protects Model"),
            ("applies", "Applies Rule"),
            ("shows", "Shows Menu"),
        ],
        required=True,
        index=True,
    )
    label = fields.Char()
    metadata_json = fields.Json(default=dict)

    _edge_uniq = models.Constraint(
        "UNIQUE(snapshot_id, source_key, target_key, edge_type)",
        "A snapshot cannot contain duplicate graph edges.",
    )


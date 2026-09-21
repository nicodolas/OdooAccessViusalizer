from odoo import fields, models


class AccessSnapshotNode(models.Model):
    _name = "oav.access.snapshot.node"
    _description = "Access Visualizer Snapshot Node"
    _order = "node_type, label, id"

    snapshot_id = fields.Many2one(
        "oav.access.snapshot", required=True, ondelete="cascade", index=True
    )
    node_key = fields.Char(required=True, index=True)
    node_type = fields.Selection(
        [
            ("category", "Module Category"),
            ("privilege", "Privilege"),
            ("user", "User"),
            ("group", "Security Group"),
            ("model", "Model"),
            ("acl", "Access Control"),
            ("rule", "Record Rule"),
            ("menu", "Menu"),
        ],
        required=True,
        index=True,
    )
    source_model = fields.Char(index=True)
    source_id = fields.Integer(index=True)
    module = fields.Char(index=True)
    category = fields.Char(index=True)
    label = fields.Char(required=True, index=True)
    technical_name = fields.Char(index=True)
    search_text = fields.Char(index=True)
    metadata_json = fields.Json(default=dict)

    _node_key_uniq = models.Constraint(
        "UNIQUE(snapshot_id, node_key)",
        "A snapshot cannot contain duplicate node keys.",
    )


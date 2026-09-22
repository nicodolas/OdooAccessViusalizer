from odoo.tests.common import TransactionCase
from odoo import fields

from .common import AccessVisualizerCase


class AccessGraphQueryTest(AccessVisualizerCase):
    def test_dashboard_has_stable_contract(self):
        result = self.Snapshot.get_dashboard_data()
        self.assertIn("latest", result)
        self.assertIn("active", result)
        self.assertIn("graph", result)
        self.assertIn("nodes", result["graph"])
        self.assertIn("edges", result["graph"])

    def test_model_focus_expands_to_access_path(self):
        snapshot = self.Snapshot.create({
            "name": "Graph path test",
            "state": "completed",
            "completed_at": fields.Datetime.now(),
        })
        self.Node.create([
            {"snapshot_id": snapshot.id, "node_key": "group:1", "node_type": "group", "label": "Sales", "metadata_json": {}},
            {"snapshot_id": snapshot.id, "node_key": "acl:1", "node_type": "acl", "label": "Sales ACL", "metadata_json": {"perm_read": True, "perm_write": True}},
            {"snapshot_id": snapshot.id, "node_key": "model:1", "node_type": "model", "label": "Order", "technical_name": "sale.order", "metadata_json": {}},
            {"snapshot_id": snapshot.id, "node_key": "rule:1", "node_type": "rule", "label": "Sales rule", "metadata_json": {"perm_read": True}},
        ])
        self.Edge.create([
            {"snapshot_id": snapshot.id, "source_key": "group:1", "target_key": "acl:1", "edge_type": "grants"},
            {"snapshot_id": snapshot.id, "source_key": "acl:1", "target_key": "model:1", "edge_type": "protects"},
            {"snapshot_id": snapshot.id, "source_key": "group:1", "target_key": "rule:1", "edge_type": "applies"},
            {"snapshot_id": snapshot.id, "source_key": "rule:1", "target_key": "model:1", "edge_type": "protects"},
        ])
        result = self.Snapshot.get_dashboard_data({"node_types": ["model"], "explore": True})
        rendered_types = {node["type"] for node in result["graph"]["nodes"]}
        self.assertEqual(result["graph"]["total_nodes"], 1)
        self.assertTrue({"model", "acl", "rule", "group"}.issubset(rendered_types))
        detail = self.Snapshot.get_node_detail(snapshot.id, "model:1")
        enabled_modes = {key for key in ("read", "write", "create", "delete") if detail["access_summary"][key]}
        self.assertEqual(enabled_modes, {"read", "write"})
        self.assertEqual(detail["access_summary"]["rule_count"], 1)
        self.assertTrue(any(item["node"]["type"] == "acl" for item in detail["relationships"]))
        filtered = self.Snapshot.get_dashboard_data({
            "node_types": ["model"],
            "permission": "write",
            "explore": True,
        })
        self.assertEqual(filtered["graph"]["total_nodes"], 1)
        self.assertTrue(any(node["id"] == "model:1" for node in filtered["graph"]["nodes"]))

    def test_snapshot_compare_reports_node_changes(self):
        baseline = self.Snapshot.create({"name": "Baseline", "state": "completed", "completed_at": fields.Datetime.now()})
        current = self.Snapshot.create({"name": "Current", "state": "completed", "completed_at": fields.Datetime.now()})
        self.Node.create([
            {"snapshot_id": baseline.id, "node_key": "group:old", "node_type": "group", "label": "Old group", "metadata_json": {}},
            {"snapshot_id": current.id, "node_key": "group:new", "node_type": "group", "label": "New group", "metadata_json": {}},
        ])
        finding_values = {
            "finding_type": "acl_complexity",
            "severity": "warning",
            "certainty": "heuristic",
            "title": "Dense ACL",
            "description": "The ACL layout is dense.",
            "fingerprint": "stable-acl-fingerprint",
        }
        self.Finding.create([{**finding_values, "snapshot_id": baseline.id}, {**finding_values, "snapshot_id": current.id}])
        result = self.Snapshot.get_snapshot_compare(current.id, baseline.id)
        self.assertEqual(result["summary"]["nodes_added"], 1)
        self.assertEqual(result["summary"]["nodes_removed"], 1)
        self.assertEqual(result["nodes"]["added"][0]["label"], "New group")
        self.assertEqual(result["summary"]["findings_changed"], 0)

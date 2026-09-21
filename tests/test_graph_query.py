from odoo.tests.common import TransactionCase

from .common import AccessVisualizerCase


class AccessGraphQueryTest(AccessVisualizerCase):
    def test_dashboard_has_stable_contract(self):
        result = self.Snapshot.get_dashboard_data()
        self.assertIn("latest", result)
        self.assertIn("active", result)
        self.assertIn("graph", result)
        self.assertIn("nodes", result["graph"])
        self.assertIn("edges", result["graph"])

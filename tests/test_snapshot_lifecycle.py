from odoo.tests.common import TransactionCase

from .common import AccessVisualizerCase


class AccessSnapshotLifecycleTest(AccessVisualizerCase):
    def test_enqueue_returns_queued_snapshot(self):
        result = self.Snapshot.enqueue_scan()
        self.assertIn(result["state"], ("queued", "running"))
        self.assertTrue(result["id"])

    def test_active_scan_is_reused(self):
        first = self.Snapshot.enqueue_scan()
        second = self.Snapshot.enqueue_scan()
        self.assertEqual(first["id"], second["id"])


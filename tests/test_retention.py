from odoo.tests.common import TransactionCase

from .common import AccessVisualizerCase


class AccessSnapshotRetentionTest(AccessVisualizerCase):
    def test_retention_constraint_accepts_five_to_ten(self):
        snapshot = self.Snapshot.create({"retention_count": 5})
        self.assertEqual(snapshot.retention_count, 5)
        snapshot.retention_count = 10
        self.assertEqual(snapshot.retention_count, 10)


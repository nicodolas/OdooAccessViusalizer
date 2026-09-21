from odoo.tests.common import TransactionCase

from ..services.normalizer import AccessSnapshotNormalizer


class AccessSnapshotNormalizerTest(TransactionCase):
    def test_node_key_is_stable(self):
        normalizer = AccessSnapshotNormalizer(self.env)
        self.assertEqual(
            normalizer.key("group", "res.groups", 42),
            "group:res.groups:42",
        )


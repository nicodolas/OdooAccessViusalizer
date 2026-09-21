from odoo.tests.common import TransactionCase


class AccessVisualizerCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Snapshot = cls.env["oav.access.snapshot"]
        cls.Node = cls.env["oav.access.snapshot.node"]
        cls.Edge = cls.env["oav.access.snapshot.edge"]
        cls.Finding = cls.env["oav.access.finding"]


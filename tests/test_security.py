from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class AccessVisualizerSecurityTest(TransactionCase):
    def test_non_admin_cannot_read_dashboard(self):
        user = self.env["res.users"].search([("id", "!=", self.env.uid)], limit=20).filtered(
            lambda candidate: not candidate.has_group("base.group_system")
        )[:1]
        if not user:
            self.skipTest("The database has no non-admin user fixture.")
        with self.assertRaises(AccessError):
            self.env["oav.access.snapshot"].with_user(user).get_dashboard_data()

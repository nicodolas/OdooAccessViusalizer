from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class AccessVisualizerSecurityTest(TransactionCase):
    def test_non_admin_cannot_read_dashboard(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Access Visualizer Test User",
            "login": "oav_security_test_user",
            "email": "oav-security-test@example.invalid",
            "share": True,
            "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        with self.assertRaises(AccessError):
            self.env["oav.access.snapshot"].with_user(user).get_dashboard_data()

    def test_non_admin_cannot_read_findings_or_node_details(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Access Visualizer Detail Test User",
            "login": "oav_security_detail_test_user",
            "email": "oav-security-detail-test@example.invalid",
            "share": True,
            "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        Snapshot = self.env["oav.access.snapshot"]
        with self.assertRaises(AccessError):
            Snapshot.with_user(user).get_findings(0)
        with self.assertRaises(AccessError):
            Snapshot.with_user(user).get_node_detail(0, "missing")

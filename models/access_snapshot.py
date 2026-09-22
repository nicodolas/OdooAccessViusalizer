import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..services.graph_query import AccessGraphQuery
from ..services.scanner import AccessSnapshotScanner

_logger = logging.getLogger(__name__)


class AccessSnapshot(models.Model):
    _name = "oav.access.snapshot"
    _description = "Odoo Access Visualizer Snapshot"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, copy=False, default="New scan")
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        required=True,
        default="queued",
        index=True,
        copy=False,
    )
    requested_by = fields.Many2one("res.users", required=True, index=True, copy=False)
    requested_at = fields.Datetime(required=True, default=fields.Datetime.now, copy=False)
    started_at = fields.Datetime(copy=False)
    completed_at = fields.Datetime(copy=False)
    failed_at = fields.Datetime(copy=False)
    error_message = fields.Text(copy=False)
    scan_duration_seconds = fields.Float(copy=False)
    node_count = fields.Integer(copy=False)
    edge_count = fields.Integer(copy=False)
    finding_count = fields.Integer(copy=False)
    retention_count = fields.Integer(default=5, required=True)
    scan_version = fields.Char(default="1", required=True, copy=False)
    node_ids = fields.One2many("oav.access.snapshot.node", "snapshot_id")
    edge_ids = fields.One2many("oav.access.snapshot.edge", "snapshot_id")
    finding_ids = fields.One2many("oav.access.finding", "snapshot_id")

    _retention_check = models.Constraint(
        "CHECK(retention_count >= 5 AND retention_count <= 10)",
        "Snapshot retention must stay between 5 and 10.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("requested_by", self.env.user.id)
            vals.setdefault("requested_at", fields.Datetime.now())
        return super().create(vals_list)

    @api.model
    def _check_visualizer_access(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only Settings administrators can use Access Visualizer."))

    @api.model
    def _active_scan_id(self):
        self.env.cr.execute(
            """
            SELECT id
              FROM oav_access_snapshot
             WHERE state IN ('queued', 'running')
             ORDER BY id
             LIMIT 1
            """
        )
        row = self.env.cr.fetchone()
        return row[0] if row else False

    @api.model
    def enqueue_scan(self):
        self._check_visualizer_access()
        # Serialize the check-and-create section so two browser clicks or two
        # concurrent workers cannot enqueue duplicate active scans.
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtext('oav_access_visualizer.enqueue_scan'))"
        )
        active_id = self._active_scan_id()
        if active_id:
            snapshot = self.browse(active_id)
        else:
            snapshot = self.create(
                {
                    "name": _("Security scan %s") % fields.Datetime.now(),
                    "state": "queued",
                    "requested_by": self.env.user.id,
                }
            )
        return snapshot._status_payload()

    @api.model
    def cron_process_queue(self):
        """Claim and process one scan without blocking a web request."""
        snapshot = self._claim_next_scan()
        if not snapshot:
            return False

        snapshot_id = snapshot.id
        started = time.monotonic()
        try:
            # Make the running state visible before the potentially long scan.
            self.env.cr.commit()
            result = AccessSnapshotScanner(self.env, snapshot).run()
            snapshot = self.browse(snapshot_id)
            snapshot.write(
                {
                    "state": "completed",
                    "completed_at": fields.Datetime.now(),
                    "scan_duration_seconds": time.monotonic() - started,
                    "node_count": result["node_count"],
                    "edge_count": result["edge_count"],
                    "finding_count": result["finding_count"],
                    "error_message": False,
                }
            )
            snapshot._apply_retention()
            self.env.cr.commit()
        except Exception as exc:
            _logger.exception("Access Visualizer scan %s failed", snapshot_id)
            self.env.cr.rollback()
            snapshot = self.browse(snapshot_id)
            snapshot.write(
                {
                    "state": "failed",
                    "failed_at": fields.Datetime.now(),
                    "scan_duration_seconds": time.monotonic() - started,
                    "error_message": str(exc)[:2000],
                }
            )
            self.env.cr.commit()
        return True

    @api.model
    def _claim_next_scan(self):
        self.env.cr.execute(
            """
            SELECT id
              FROM oav_access_snapshot
             WHERE state = 'queued'
             ORDER BY id
             LIMIT 1
             FOR UPDATE SKIP LOCKED
            """
        )
        row = self.env.cr.fetchone()
        if not row:
            return self.browse()
        snapshot = self.browse(row[0])
        snapshot.write({"state": "running", "started_at": fields.Datetime.now()})
        return snapshot

    def _apply_retention(self):
        self.ensure_one()
        successful = self.search(
            [("state", "=", "completed")], order="completed_at desc, id desc"
        )
        stale = successful[self.retention_count :]
        if stale:
            stale.unlink()

    def _status_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "requested_at": self.requested_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failed_at": self.failed_at,
            "error_message": self.error_message,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "finding_count": self.finding_count,
        }

    @api.model
    def get_dashboard_data(self, filters=None):
        self._check_visualizer_access()
        latest = self.search(
            [("state", "=", "completed")], order="completed_at desc, id desc", limit=1
        )
        active = self.search(
            [("state", "in", ["queued", "running"])], order="id desc", limit=1
        )
        recent_snapshots = self.search(
            [("state", "=", "completed")], order="completed_at desc, id desc", limit=10
        )
        graph_query = AccessGraphQuery(self.env)
        graph = graph_query.get_graph(latest, filters or {}) if latest else {
            "nodes": [],
            "edges": [],
            "budget_exceeded": False,
            "needs_focus": False,
            "total_nodes": 0,
            "total_edges": 0,
        }
        return {
            "latest": latest._status_payload() if latest else None,
            "active": active._status_payload() if active else None,
            "recent_snapshots": [snapshot._status_payload() for snapshot in recent_snapshots],
            "overview": graph_query.get_overview(latest) if latest else {
                "layers": [],
                "severity_counts": {},
                "finding_type_counts": [],
                "top_findings": [],
            },
            "graph": graph,
        }

    @api.model
    def get_snapshot_status(self, snapshot_id):
        self._check_visualizer_access()
        snapshot = self.browse(snapshot_id).exists()
        if not snapshot:
            raise UserError(_("The requested snapshot no longer exists."))
        return snapshot._status_payload()

    @api.model
    def get_node_detail(self, snapshot_id, node_key):
        self._check_visualizer_access()
        snapshot = self.browse(snapshot_id).exists()
        if not snapshot or snapshot.state != "completed":
            raise UserError(_("Only a completed snapshot can be inspected."))
        return AccessGraphQuery(self.env).get_node_detail(snapshot, node_key)

    @api.model
    def get_findings(self, snapshot_id, filters=None):
        self._check_visualizer_access()
        snapshot = self.browse(snapshot_id).exists()
        if not snapshot or snapshot.state != "completed":
            return []
        return AccessGraphQuery(self.env).get_findings(snapshot, filters or {})

    @api.model
    def get_snapshot_compare(self, current_id, baseline_id):
        self._check_visualizer_access()
        current = self.browse(current_id).exists()
        baseline = self.browse(baseline_id).exists()
        if not current or not baseline or current.state != "completed" or baseline.state != "completed":
            raise UserError(_("Only completed snapshots can be compared."))
        if current.id == baseline.id:
            raise UserError(_("Choose two different snapshots to compare."))
        return AccessGraphQuery(self.env).compare_snapshots(current, baseline)

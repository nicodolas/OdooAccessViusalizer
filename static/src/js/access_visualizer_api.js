export class AccessVisualizerApi {
    constructor(orm) {
        this.orm = orm;
        this.model = "oav.access.snapshot";
    }

    dashboard(filters = {}) {
        return this.orm.call(this.model, "get_dashboard_data", [filters]);
    }

    enqueueScan() {
        return this.orm.call(this.model, "enqueue_scan", []);
    }

    status(snapshotId) {
        return this.orm.call(this.model, "get_snapshot_status", [snapshotId]);
    }

    nodeDetail(snapshotId, nodeKey) {
        return this.orm.call(this.model, "get_node_detail", [snapshotId, nodeKey]);
    }

    findings(snapshotId, filters = {}) {
        return this.orm.call(this.model, "get_findings", [snapshotId, filters]);
    }
}


import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { AccessVisualizerApi } from "./access_visualizer_api";
import { AccessGraphRenderer } from "./graph_renderer";

export class AccessVisualizerAction extends Component {
    static template = "odoo_access_visualizer.AccessVisualizerAction";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.api = new AccessVisualizerApi(this.orm);
        this.graphRef = useRef("graph");
        this.state = useState({
            loading: true,
            error: null,
            dashboard: null,
            graph: { nodes: [], edges: [] },
            findings: [],
            selectedNode: null,
            filters: { search: "", module: "", node_types: [] },
        });
        this.pollTimer = null;
        this.renderer = null;
        onWillStart(() => this.reload());
        onMounted(() => {
            this.renderer = new AccessGraphRenderer(this.graphRef.el, (key) => this.selectNode(key));
            this.renderGraph();
            this.startPollingIfNeeded();
        });
        onWillUnmount(() => {
            this.stopPolling();
            this.renderer?.destroy();
        });
    }

    async reload() {
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.dashboard = await this.api.dashboard(this.state.filters);
            this.state.graph = this.state.dashboard.graph || { nodes: [], edges: [] };
            const latest = this.state.dashboard.latest;
            this.state.findings = latest ? await this.api.findings(latest.id) : [];
        } catch (error) {
            this.state.error = error.message || "Unable to load Access Visualizer.";
        } finally {
            this.state.loading = false;
            this.renderGraph();
            this.startPollingIfNeeded();
        }
    }

    renderGraph() {
        if (this.renderer && !this.state.loading) {
            this.renderer.render(this.state.graph);
        }
    }

    async enqueueScan() {
        try {
            await this.api.enqueueScan();
            this.notification.add("Security scan queued.", { type: "success" });
            await this.reload();
        } catch (error) {
            this.state.error = error.message || "Unable to queue a scan.";
        }
    }

    async applyFilters() {
        await this.reload();
    }

    async selectNode(nodeKey) {
        const latest = this.state.dashboard?.latest;
        if (!latest) {
            return;
        }
        try {
            this.state.selectedNode = await this.api.nodeDetail(latest.id, nodeKey);
        } catch (error) {
            this.state.error = error.message || "Unable to load node details.";
        }
    }

    formatJson(value) {
        return JSON.stringify(value || {}, null, 2);
    }

    startPollingIfNeeded() {
        if (this.state.dashboard?.active && !this.pollTimer) {
            this.pollTimer = setInterval(() => this.reload(), 5000);
        } else if (!this.state.dashboard?.active) {
            this.stopPolling();
        }
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }
}

registry.category("actions").add("odoo_access_visualizer", AccessVisualizerAction);

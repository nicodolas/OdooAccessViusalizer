import { Component, onPatched, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
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
            graph: { nodes: [], edges: [], needs_focus: false },
            findings: [],
            selectedNode: null,
            activeTab: "overview",
            filters: {
                search: "",
                module: "",
                node_types: [],
                explore: false,
            },
        });
        this.pollTimer = null;
        this.renderer = null;
        this.renderedGraphKey = null;
        onWillStart(() => this.reload());
        onPatched(() => {
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
            this.state.graph = this.state.dashboard.graph || { nodes: [], edges: [], needs_focus: false };
            const latest = this.state.dashboard.latest;
            this.state.findings = latest
                ? (this.state.dashboard.overview?.top_findings || await this.api.findings(latest.id))
                : [];
        } catch (error) {
            this.state.error = error.message || _t("Unable to load Access Visualizer.");
        } finally {
            this.state.loading = false;
            this.renderGraph();
            this.startPollingIfNeeded();
        }
    }

    renderGraph() {
        if (!this.graphRef.el) {
            if (this.renderer) {
                this.renderer.destroy();
                this.renderer = null;
                this.renderedGraphKey = null;
            }
            return;
        }
        if (this.state.loading) {
            return;
        }
        if (!this.renderer) {
            this.renderer = new AccessGraphRenderer(this.graphRef.el, (key) => this.selectNode(key));
        }
        const graphKey = JSON.stringify({
            needsFocus: this.state.graph.needs_focus,
            nodes: this.state.graph.nodes.map((node) => node.id),
            edges: this.state.graph.edges.map((edge) => edge.id),
        });
        if (graphKey !== this.renderedGraphKey) {
            this.renderedGraphKey = graphKey;
            this.renderer.render(this.state.graph);
        }
    }

    setTab(event) {
        const tab = event.currentTarget.dataset.tab;
        this.state.activeTab = tab;
        if (tab === "findings" && this.state.dashboard?.latest) {
            this.api.findings(this.state.dashboard.latest.id, { limit: 500 })
                .then((findings) => { this.state.findings = findings; })
                .catch((error) => { this.state.error = error.message; });
        }
    }

    chooseLayer(event) {
        const nodeType = event.target.value;
        this.state.filters.node_types = nodeType ? [nodeType] : [];
        this.state.filters.explore = Boolean(nodeType || this.state.filters.search);
    }

    async applyGraphFilters() {
        this.state.filters.explore = Boolean(
            this.state.filters.search || this.state.filters.node_types.length
        );
        await this.reload();
    }

    async openGraphLayer(event) {
        this.state.activeTab = "graph";
        this.state.filters.node_types = [event.currentTarget.dataset.layer];
        this.state.filters.explore = true;
        await this.reload();
    }

    async clearGraphFilters() {
        this.state.filters.search = "";
        this.state.filters.module = "";
        this.state.filters.node_types = [];
        this.state.filters.explore = false;
        await this.reload();
    }

    async enqueueScan() {
        try {
            await this.api.enqueueScan();
            this.notification.add(_t("Security scan queued."), { type: "success" });
            await this.reload();
        } catch (error) {
            this.state.error = error.message || _t("Unable to queue a scan.");
        }
    }

    async selectNode(nodeKey) {
        const latest = this.state.dashboard?.latest;
        if (!latest) {
            return;
        }
        try {
            this.state.selectedNode = await this.api.nodeDetail(latest.id, nodeKey);
        } catch (error) {
            this.state.error = error.message || _t("Unable to load node details.");
        }
    }

    async focusFinding(event) {
        const findingId = Number(event.currentTarget.dataset.findingId);
        const finding = this.state.findings.find((item) => item.id === findingId);
        if (!finding) {
            return;
        }
        this.state.activeTab = "graph";
        this.state.filters.search = finding.model_name || "";
        this.state.filters.node_types = finding.model_name ? ["model"] : [];
        this.state.filters.explore = true;
        await this.reload();
    }

    formatJson(value) {
        return JSON.stringify(value || {}, null, 2);
    }

    getAccessModes(metadata) {
        const labels = {
            perm_read: _t("Read"),
            perm_write: _t("Write"),
            perm_create: _t("Create"),
            perm_unlink: _t("Delete"),
        };
        return Object.entries(labels)
            .filter(([key]) => metadata?.[key])
            .map(([, label]) => label);
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

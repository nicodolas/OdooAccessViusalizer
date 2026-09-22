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
            compare: null,
            compareBaselineId: null,
            selectedNode: null,
            viewMode: "path",
            activeTab: "overview",
            filters: {
                search: "",
                module: "",
                permission: "",
                node_types: [],
                explore: false,
            },
        });
        this.pollTimer = null;
        this.renderer = null;
        this.renderedGraphKey = null;
        this.reloadToken = 0;
        this.permissionMatrixKey = null;
        this.permissionMatrix = [];
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
        const requestToken = ++this.reloadToken;
        this.state.loading = true;
        this.state.error = null;
        try {
            this.state.dashboard = await this.api.dashboard(this.state.filters);
            if (requestToken !== this.reloadToken) return;
            this.state.graph = this.state.dashboard.graph || { nodes: [], edges: [], needs_focus: false };
            this.permissionMatrixKey = null;
            if (this.state.compare?.current?.id !== this.state.dashboard.latest?.id) {
                this.state.compare = null;
                this.state.compareBaselineId = null;
            }
            const latest = this.state.dashboard.latest;
            const findings = latest
                ? (this.state.dashboard.overview?.top_findings || await this.api.findings(latest.id))
                : [];
            if (requestToken !== this.reloadToken) return;
            this.state.findings = findings;
        } catch (error) {
            if (requestToken === this.reloadToken) {
                this.state.error = error.message || _t("Unable to load Access Visualizer.");
            }
        } finally {
            if (requestToken === this.reloadToken) {
                this.state.loading = false;
                this.renderGraph();
                this.startPollingIfNeeded();
            }
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
            viewMode: this.state.viewMode,
            selectedNode: this.state.selectedNode?.node?.id || null,
            nodes: this.state.graph.nodes.map((node) => node.id),
            edges: this.state.graph.edges.map((edge) => edge.id),
        });
        if (graphKey !== this.renderedGraphKey) {
            this.renderedGraphKey = graphKey;
            this.renderer.render(this.state.graph, {
                mode: this.state.viewMode,
                selectedKey: this.state.selectedNode?.node?.id,
            });
            if (this.state.selectedNode && this.state.viewMode !== "matrix") {
                this.applyHighlight();
            }
        }
    }

    setTab(event) {
        const tab = event.currentTarget.dataset.tab;
        this.state.activeTab = tab;
        if (tab === "compare") {
            const snapshots = this.state.dashboard?.recent_snapshots || [];
            this.state.compareBaselineId = this.state.compareBaselineId || snapshots.find((item) => item.id !== this.state.dashboard.latest.id)?.id || null;
            this.loadCompare();
        }
        if (tab === "findings" && this.state.dashboard?.latest) {
            this.api.findings(this.state.dashboard.latest.id, { limit: 500 })
                .then((findings) => { this.state.findings = findings; })
                .catch((error) => { this.state.error = error.message; });
        }
    }

    chooseLayer(event) {
        const nodeType = event.target.value;
        this.state.filters.node_types = nodeType ? [nodeType] : [];
        this.state.filters.explore = Boolean(nodeType || this.state.filters.search || this.state.filters.permission);
    }

    async chooseCompareBaseline(event) {
        this.state.compareBaselineId = Number(event.target.value) || null;
        this.state.compare = null;
        await this.loadCompare();
    }

    async loadCompare() {
        const currentId = this.state.dashboard?.latest?.id;
        const baselineId = this.state.compareBaselineId;
        if (!currentId || !baselineId) return;
        try {
            const compare = await this.api.compare(currentId, baselineId);
            if (baselineId !== this.state.compareBaselineId) return;
            this.state.compare = compare;
        } catch (error) {
            if (baselineId !== this.state.compareBaselineId) return;
            this.state.error = error.message || _t("Unable to compare snapshots.");
        }
    }

    choosePermission(event) {
        this.state.filters.permission = event.target.value;
        this.state.filters.explore = Boolean(
            this.state.filters.search || this.state.filters.node_types.length || this.state.filters.permission
        );
    }

    async applyGraphFilters() {
        this.state.filters.explore = Boolean(
            this.state.filters.search || this.state.filters.node_types.length || this.state.filters.permission
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
        this.state.filters.permission = "";
        this.state.filters.node_types = [];
        this.state.filters.explore = false;
        this.state.viewMode = "path";
        this.state.selectedNode = null;
        this.permissionMatrixKey = null;
        this.renderer?.highlightPath(null);
        this.renderedGraphKey = null;
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
            this.applyHighlight();
        } catch (error) {
            this.state.error = error.message || _t("Unable to load node details.");
        }
    }

    chooseViewMode(event) {
        this.state.viewMode = event.target.value;
        this.state.selectedNode = null;
        this.renderer?.highlightPath(null);
        this.renderedGraphKey = null;
        this.renderGraph();
    }

    getPermissionMatrix() {
        const graphKey = JSON.stringify([
            this.state.graph.nodes.map((node) => node.id),
            this.state.graph.edges.map((edge) => edge.id),
        ]);
        if (graphKey === this.permissionMatrixKey) return this.permissionMatrix;
        const nodes = new Map((this.state.graph.nodes || []).map((node) => [node.id, node]));
        const aclByGroup = new Map();
        const rows = new Map();
        for (const edge of this.state.graph.edges || []) {
            const source = nodes.get(edge.source);
            const target = nodes.get(edge.target);
            if (edge.type === "grants" && source?.type === "group" && target?.type === "acl") {
                aclByGroup.set(edge.source, [...(aclByGroup.get(edge.source) || []), target]);
            }
        }
        for (const [rootGroupId] of aclByGroup) {
            const effectiveGroups = new Set([rootGroupId]);
            const frontier = [rootGroupId];
            while (frontier.length) {
                const groupId = frontier.pop();
                for (const edge of this.state.graph.edges || []) {
                    if (edge.type === "implied" && edge.source === groupId && !effectiveGroups.has(edge.target)) {
                        effectiveGroups.add(edge.target);
                        frontier.push(edge.target);
                    }
                }
            }
            const acls = [...effectiveGroups].flatMap((groupId) => aclByGroup.get(groupId) || []);
            for (const acl of acls) {
                const modelEdge = (this.state.graph.edges || []).find(
                    (edge) => edge.type === "protects" && edge.source === acl.id && nodes.get(edge.target)?.type === "model"
                );
                const model = modelEdge && nodes.get(modelEdge.target);
                if (!model) continue;
                const key = `${rootGroupId}:${model.id}`;
                const current = rows.get(key) || {
                    group: nodes.get(rootGroupId).label,
                    model: model.label,
                    read: false,
                    write: false,
                    create: false,
                    delete: false,
                    rules: 0,
                };
                const metadata = acl.metadata || {};
                current.read ||= Boolean(metadata.perm_read);
                current.write ||= Boolean(metadata.perm_write);
                current.create ||= Boolean(metadata.perm_create);
                current.delete ||= Boolean(metadata.perm_unlink);
                rows.set(key, current);
            }
        }
        this.permissionMatrix = [...rows.values()]
            .sort((left, right) => `${left.group}${left.model}`.localeCompare(`${right.group}${right.model}`))
            .map((row, index) => ({ ...row, key: `${row.group}:${row.model}:${index}` }));
        this.permissionMatrixKey = graphKey;
        return this.permissionMatrix;
    }

    applyHighlight() {
        if (!this.renderer || !this.state.selectedNode || this.state.viewMode === "matrix") return;
        this.renderer.highlightPath(
            this.state.selectedNode.node.id,
            (this.state.selectedNode.relationships || []).map((item) => item.node.id)
        );
    }

    clearSelection() {
        this.state.selectedNode = null;
        this.renderer?.highlightPath(null);
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

    getAccessModes(summary) {
        const labels = {
            read: _t("Read"),
            write: _t("Write"),
            create: _t("Create"),
            delete: _t("Delete"),
        };
        return Object.entries(labels)
            .filter(([key]) => summary?.[key])
            .map(([key, label]) => ({ key, label }));
    }

    getGraphSummary(graph) {
        const total = graph?.total_nodes || 0;
        const rendered = graph?.rendered_nodes || 0;
        return rendered && rendered !== total
            ? `${total} ${_t("matching objects")} · ${rendered} ${_t("rendered with context")}`
            : `${total} ${_t("objects in focus")}`;
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

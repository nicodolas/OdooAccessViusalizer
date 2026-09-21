const SVG_NS = "http://www.w3.org/2000/svg";

const COLORS = {
    category: "#2563eb",
    privilege: "#7c3aed",
    user: "#ca8a04",
    group: "#16a34a",
    model: "#ea580c",
    acl: "#64748b",
    rule: "#dc2626",
    menu: "#92400e",
};

export class AccessGraphRenderer {
    constructor(container, onNodeClick) {
        this.container = container;
        this.onNodeClick = onNodeClick;
        this.cy = null;
        this.svg = null;
        this.transform = { x: 0, y: 0, scale: 1 };
        this.drag = null;
    }

    destroy() {
        if (this.cy) {
            this.cy.destroy();
            this.cy = null;
        }
        if (this.svg) {
            this.svg.replaceChildren();
            this.svg = null;
        }
        this.container.replaceChildren();
    }

    render(graph) {
        this.destroy();
        if (window.cytoscape) {
            this._renderCytoscape(graph);
            return;
        }
        const svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("class", "oav_graph_svg");
        svg.setAttribute("viewBox", "0 0 1200 720");
        svg.setAttribute("role", "img");
        svg.setAttribute("aria-label", "Access relationship graph");
        const viewport = document.createElementNS(SVG_NS, "g");
        svg.appendChild(viewport);
        this.svg = svg;
        this.viewport = viewport;
        this._installNavigation(svg);

        const nodes = graph.nodes || [];
        const positions = new Map();
        const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)));
        const cellWidth = 1120 / columns;
        const rows = Math.max(1, Math.ceil(nodes.length / columns));
        const cellHeight = Math.max(70, 660 / rows);
        nodes.forEach((node, index) => {
            positions.set(node.id, {
                x: 40 + (index % columns) * cellWidth + cellWidth / 2,
                y: 30 + Math.floor(index / columns) * cellHeight + cellHeight / 2,
            });
        });

        for (const edge of graph.edges || []) {
            const source = positions.get(edge.source);
            const target = positions.get(edge.target);
            if (!source || !target) {
                continue;
            }
            const line = document.createElementNS(SVG_NS, "line");
            line.setAttribute("x1", source.x);
            line.setAttribute("y1", source.y);
            line.setAttribute("x2", target.x);
            line.setAttribute("y2", target.y);
            line.setAttribute("class", `oav_edge oav_edge_${edge.type}`);
            line.setAttribute("data-edge-type", edge.type);
            viewport.appendChild(line);
        }

        for (const node of nodes) {
            const point = positions.get(node.id);
            const group = document.createElementNS(SVG_NS, "g");
            group.setAttribute("class", "oav_node");
            group.setAttribute("tabindex", "0");
            group.setAttribute("role", "button");
            group.dataset.nodeKey = node.key;
            group.addEventListener("click", () => this.onNodeClick(node.key));
            group.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    this.onNodeClick(node.key);
                }
            });
            const shape = document.createElementNS(SVG_NS, "circle");
            shape.setAttribute("cx", point.x);
            shape.setAttribute("cy", point.y);
            shape.setAttribute("r", node.type === "model" ? "19" : "15");
            shape.setAttribute("fill", COLORS[node.type] || "#475569");
            shape.setAttribute("class", `oav_node_shape oav_node_${node.type}`);
            group.appendChild(shape);
            const label = document.createElementNS(SVG_NS, "text");
            label.setAttribute("x", point.x);
            label.setAttribute("y", point.y + 34);
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("class", "oav_node_label");
            label.textContent = this._truncate(node.label || node.key, 22);
            group.appendChild(label);
            viewport.appendChild(group);
        }
        this.container.appendChild(svg);
    }

    _renderCytoscape(graph) {
        const elements = [
            ...(graph.nodes || []).map((node) => ({
                data: { id: node.id, label: node.label || node.id, type: node.type },
            })),
            ...(graph.edges || []).map((edge) => ({
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    type: edge.type,
                },
            })),
        ];
        this.cy = window.cytoscape({
            container: this.container,
            elements,
            style: [
                {
                    selector: "node",
                    style: {
                        "background-color": "#475569",
                        label: "data(label)",
                        color: "#334155",
                        "font-size": "10px",
                        "text-valign": "bottom",
                        "text-margin-y": 6,
                        "text-wrap": "ellipsis",
                        "text-max-width": 110,
                        width: 28,
                        height: 28,
                    },
                },
                { selector: 'node[type = "category"]', style: { "background-color": "#2563eb", width: 38, height: 38 } },
                { selector: 'node[type = "privilege"]', style: { "background-color": "#7c3aed", width: 34, height: 34 } },
                { selector: 'node[type = "user"]', style: { "background-color": "#ca8a04" } },
                { selector: 'node[type = "group"]', style: { "background-color": "#16a34a" } },
                { selector: 'node[type = "model"]', style: { "background-color": "#ea580c", shape: "rectangle" } },
                { selector: 'node[type = "acl"]', style: { "background-color": "#64748b", width: 20, height: 20 } },
                { selector: 'node[type = "rule"]', style: { "background-color": "#dc2626", shape: "triangle" } },
                { selector: 'node[type = "menu"]', style: { "background-color": "#92400e", shape: "hexagon" } },
                {
                    selector: "edge",
                    style: {
                        width: 1,
                        "line-color": "#94a3b8",
                        "target-arrow-color": "#94a3b8",
                        "target-arrow-shape": "triangle",
                        "curve-style": "bezier",
                    },
                },
                { selector: 'edge[type = "implied"]', style: { width: 2, "line-color": "#16a34a", "target-arrow-color": "#16a34a" } },
                { selector: 'edge[type = "applies"]', style: { "line-color": "#dc2626", "target-arrow-color": "#dc2626" } },
            ],
            layout: {
                name: (graph.nodes || []).length > 500 ? "grid" : "breadthfirst",
                directed: true,
                padding: 24,
                animate: false,
            },
            wheelSensitivity: 0.2,
        });
        this.cy.on("tap", "node", (event) => this.onNodeClick(event.target.id()));
    }

    _truncate(value, length) {
        return value.length > length ? `${value.slice(0, length - 1)}…` : value;
    }

    _installNavigation(svg) {
        svg.addEventListener("wheel", (event) => {
            event.preventDefault();
            this.transform.scale = Math.min(
                2.5,
                Math.max(0.35, this.transform.scale + (event.deltaY < 0 ? 0.1 : -0.1))
            );
            this._applyTransform();
        }, { passive: false });
        svg.addEventListener("pointerdown", (event) => {
            if (event.target.closest(".oav_node")) {
                return;
            }
            this.drag = { x: event.clientX, y: event.clientY };
            svg.setPointerCapture(event.pointerId);
        });
        svg.addEventListener("pointermove", (event) => {
            if (!this.drag) {
                return;
            }
            this.transform.x += event.clientX - this.drag.x;
            this.transform.y += event.clientY - this.drag.y;
            this.drag = { x: event.clientX, y: event.clientY };
            this._applyTransform();
        });
        svg.addEventListener("pointerup", () => { this.drag = null; });
        svg.addEventListener("pointercancel", () => { this.drag = null; });
    }

    _applyTransform() {
        if (this.viewport) {
            this.viewport.setAttribute(
                "transform",
                `translate(${this.transform.x} ${this.transform.y}) scale(${this.transform.scale})`
            );
        }
    }
}

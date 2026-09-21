class AccessGraphQuery:
    NODE_LIMIT = 2000
    EDGE_LIMIT = 10000

    def __init__(self, env):
        self.env = env

    @staticmethod
    def _node_payload(node):
        return {
            "id": node.node_key,
            "key": node.node_key,
            "type": node.node_type,
            "label": node.label,
            "module": node.module or "unknown",
            "category": node.category or "",
            "source_model": node.source_model or "",
            "source_id": node.source_id or 0,
            "technical_name": node.technical_name or "",
            "metadata": node.metadata_json or {},
        }

    @staticmethod
    def _edge_payload(edge):
        return {
            "id": f"{edge.source_key}>{edge.target_key}:{edge.edge_type}",
            "source": edge.source_key,
            "target": edge.target_key,
            "type": edge.edge_type,
            "label": edge.label or "",
            "metadata": edge.metadata_json or {},
        }

    def get_graph(self, snapshot, filters):
        if not snapshot:
            return {"nodes": [], "edges": [], "budget_exceeded": False, "total_nodes": 0, "total_edges": 0}
        Node = self.env["oav.access.snapshot.node"].sudo()
        Edge = self.env["oav.access.snapshot.edge"].sudo()
        domain = [("snapshot_id", "=", snapshot.id)]
        node_types = filters.get("node_types") or []
        if node_types:
            domain.append(("node_type", "in", node_types))
        if filters.get("search"):
            search = filters["search"]
            domain.extend(["|", ("label", "ilike", search), ("search_text", "ilike", search)])
        if filters.get("module"):
            domain.append(("module", "=", filters["module"]))

        total_nodes = Node.search_count(domain)
        nodes = Node.search(domain, order="node_type, label, id", limit=self.NODE_LIMIT + 1)
        budget_exceeded = len(nodes) > self.NODE_LIMIT
        if budget_exceeded:
            nodes = nodes[: self.NODE_LIMIT]
        keys = nodes.mapped("node_key")
        edge_domain = [("snapshot_id", "=", snapshot.id)]
        if keys:
            edge_domain.extend([("source_key", "in", keys), ("target_key", "in", keys)])
        else:
            edge_domain.append(("id", "=", 0))
        total_edges = Edge.search_count(edge_domain)
        edges = Edge.search(edge_domain, order="edge_type, id", limit=self.EDGE_LIMIT + 1)
        if len(edges) > self.EDGE_LIMIT:
            budget_exceeded = True
            edges = edges[: self.EDGE_LIMIT]
        return {
            "nodes": [self._node_payload(node) for node in nodes],
            "edges": [self._edge_payload(edge) for edge in edges],
            "budget_exceeded": budget_exceeded,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "render_limits": {"nodes": self.NODE_LIMIT, "edges": self.EDGE_LIMIT},
        }

    def get_node_detail(self, snapshot, node_key):
        Node = self.env["oav.access.snapshot.node"].sudo()
        node = Node.search([( "snapshot_id", "=", snapshot.id), ("node_key", "=", node_key)], limit=1)
        if not node:
            return None
        Edge = self.env["oav.access.snapshot.edge"].sudo()
        edges = Edge.search(
            [
                ("snapshot_id", "=", snapshot.id),
                "|",
                ("source_key", "=", node_key),
                ("target_key", "=", node_key),
            ],
            limit=200,
        )
        return {"node": self._node_payload(node), "edges": [self._edge_payload(edge) for edge in edges]}

    def get_findings(self, snapshot, filters):
        Finding = self.env["oav.access.finding"].sudo()
        domain = [("snapshot_id", "=", snapshot.id)]
        if filters.get("severity"):
            domain.append(("severity", "=", filters["severity"]))
        if filters.get("finding_type"):
            domain.append(("finding_type", "=", filters["finding_type"]))
        findings = Finding.search(domain, order="severity desc, certainty, id", limit=500)
        return [
            {
                "id": finding.id,
                "type": finding.finding_type,
                "severity": finding.severity,
                "certainty": finding.certainty,
                "title": finding.title,
                "description": finding.description,
                "recommendation": finding.recommendation or "",
                "model_name": finding.model_name or "",
                "evidence": finding.evidence_json or {},
                "node_keys": finding.affected_node_keys or [],
                "edge_keys": finding.affected_edge_keys or [],
            }
            for finding in findings
        ]


class AccessGraphQuery:
    NODE_LIMIT = 250
    EDGE_LIMIT = 1500
    SEED_LIMIT = 50
    EXPANSION_HOPS = 3

    NODE_LABELS = {
        "category": "Module categories",
        "privilege": "Privileges",
        "user": "Users",
        "group": "Security groups",
        "model": "Models",
        "acl": "Access controls",
        "rule": "Record rules",
        "menu": "Menus",
    }

    FINDING_LABELS = {
        "implied_overlap": "Implied group overlap",
        "acl_redundancy": "ACL redundancy",
        "acl_complexity": "ACL complexity",
        "rule_duplicate": "Duplicate record rule",
        "rule_potential_conflict": "Potential rule interaction",
    }

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
            return {
                "nodes": [],
                "edges": [],
                "budget_exceeded": False,
                "needs_focus": False,
                "total_nodes": 0,
                "total_edges": 0,
            }
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
        total_edges = Edge.search_count([("snapshot_id", "=", snapshot.id)])
        if not filters.get("explore"):
            return {
                "nodes": [],
                "edges": [],
                "budget_exceeded": total_nodes > self.NODE_LIMIT,
                "needs_focus": bool(total_nodes),
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "render_limits": {"nodes": self.NODE_LIMIT, "edges": self.EDGE_LIMIT},
            }

        seed_limit = min(self.NODE_LIMIT, self.SEED_LIMIT)
        seed_nodes = Node.search(domain, order="node_type, label, id", limit=seed_limit + 1)
        seed_count = total_nodes
        budget_exceeded = seed_count > seed_limit
        ordered_keys = list(seed_nodes[:seed_limit].mapped("node_key"))
        known_keys = set(ordered_keys)

        # Expand up to three permission hops so model focus can reach
        # Model -> ACL/Rule -> Group -> User/Menu/Privilege.
        for _hop in range(self.EXPANSION_HOPS):
            if not ordered_keys:
                break
            neighborhood_edges = Edge.search(
                [
                    ("snapshot_id", "=", snapshot.id),
                    "|",
                    ("source_key", "in", ordered_keys),
                    ("target_key", "in", ordered_keys),
                ],
                order="id",
                limit=self.EDGE_LIMIT * 2 + 1,
            )
            added = 0
            for edge in neighborhood_edges:
                for key in (edge.source_key, edge.target_key):
                    if key not in known_keys:
                        known_keys.add(key)
                        if len(ordered_keys) < self.NODE_LIMIT:
                            ordered_keys.append(key)
                        else:
                            budget_exceeded = True
                        added += 1
            if not added:
                break

        node_domain = [("snapshot_id", "=", snapshot.id), ("node_key", "in", ordered_keys)]
        nodes = Node.search(node_domain, order="node_type, label, id")
        keys = nodes.mapped("node_key")
        edge_domain = [("snapshot_id", "=", snapshot.id)]
        if keys:
            edge_domain.extend([("source_key", "in", keys), ("target_key", "in", keys)])
        else:
            edge_domain.append(("id", "=", 0))
        edges = Edge.search(edge_domain, order="edge_type, id", limit=self.EDGE_LIMIT + 1)
        if len(edges) > self.EDGE_LIMIT:
            budget_exceeded = True
            edges = edges[: self.EDGE_LIMIT]
        return {
            "nodes": [self._node_payload(node) for node in nodes],
            "edges": [self._edge_payload(edge) for edge in edges],
            "budget_exceeded": budget_exceeded,
            "needs_focus": False,
            "total_nodes": total_nodes,
            "rendered_nodes": len(nodes),
            "total_edges": total_edges,
            "seed_count": seed_count,
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
        limit = min(int(filters.get("limit", 500)), 500)
        findings = Finding.search(domain, order="severity desc, certainty, id", limit=limit)
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

    def get_overview(self, snapshot):
        if not snapshot:
            return {
                "layers": [],
                "severity_counts": {},
                "finding_type_counts": [],
                "top_findings": [],
            }
        Node = self.env["oav.access.snapshot.node"].sudo()
        Finding = self.env["oav.access.finding"].sudo()
        layer_rows = Node.read_group(
            [("snapshot_id", "=", snapshot.id)],
            ["node_type"],
            ["node_type"],
        )
        layer_counts = {
            row["node_type"]: row["node_type_count"]
            for row in layer_rows
            if row.get("node_type")
        }
        layers = [
            {"type": node_type, "label": label, "count": layer_counts.get(node_type, 0)}
            for node_type, label in self.NODE_LABELS.items()
        ]
        severity_rows = Finding.read_group(
            [("snapshot_id", "=", snapshot.id)],
            ["severity"],
            ["severity"],
        )
        severity_counts = {
            row["severity"]: row["severity_count"]
            for row in severity_rows
            if row.get("severity")
        }
        type_rows = Finding.read_group(
            [("snapshot_id", "=", snapshot.id)],
            ["finding_type"],
            ["finding_type"],
        )
        finding_type_counts = [
            {
                "type": row["finding_type"],
                "label": self.FINDING_LABELS.get(row["finding_type"], row["finding_type"]),
                "count": row["finding_type_count"],
            }
            for row in type_rows
            if row.get("finding_type")
        ]
        return {
            "layers": layers,
            "severity_counts": severity_counts,
            "finding_type_counts": sorted(
                finding_type_counts, key=lambda row: row["count"], reverse=True
            ),
            "top_findings": self.get_findings(snapshot, {"limit": 5}),
        }

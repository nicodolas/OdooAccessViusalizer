import json


class AccessGraphQuery:
    # Keep the first visual frame legible. Users can narrow the layer/search
    # filters to inspect the complete set without turning the map into a wall
    # of overlapping labels.
    NODE_LIMIT = 96
    EDGE_LIMIT = 800
    SEED_LIMIT = 32
    EXPANSION_HOPS = 2

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
                "rendered_nodes": 0,
                "rendered_edges": 0,
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
        permission = filters.get("permission")
        if permission and node_types == ["model"]:
            permission_model_keys = self._model_keys_for_permission(snapshot, permission, Node, Edge)
            domain.append(("node_key", "in", list(permission_model_keys) or [False]))

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
                "rendered_nodes": 0,
                "rendered_edges": 0,
                "render_limits": {"nodes": self.NODE_LIMIT, "edges": self.EDGE_LIMIT},
            }

        # Filters define the investigation seeds. The visible graph then
        # expands through neighbouring nodes so a model query still explains
        # its groups, ACLs and record rules instead of showing isolated dots.
        seed_records = Node.search(domain, order="node_type, label, id", limit=self.SEED_LIMIT + 1)
        budget_exceeded = len(seed_records) > self.SEED_LIMIT
        seed_records = seed_records[: self.SEED_LIMIT]
        nodes_by_key = {node.node_key: node for node in seed_records}
        frontier = set(nodes_by_key)
        edge_by_key = {}

        for _hop in range(self.EXPANSION_HOPS):
            if not frontier or len(nodes_by_key) >= self.NODE_LIMIT:
                break
            edge_domain = [
                ("snapshot_id", "=", snapshot.id),
                "|",
                ("source_key", "in", list(frontier)),
                ("target_key", "in", list(frontier)),
            ]
            nearby_edges = Edge.search(edge_domain, order="edge_type, id", limit=self.EDGE_LIMIT + 1)
            if len(nearby_edges) > self.EDGE_LIMIT:
                budget_exceeded = True
                nearby_edges = nearby_edges[: self.EDGE_LIMIT]
            next_keys = set()
            for edge in nearby_edges:
                edge_by_key[edge.id] = edge
                other_key = edge.target_key if edge.source_key in frontier else edge.source_key
                if other_key not in nodes_by_key:
                    next_keys.add(other_key)
            if not next_keys:
                break
            room = self.NODE_LIMIT - len(nodes_by_key)
            if len(next_keys) > room:
                budget_exceeded = True
                next_keys = set(sorted(next_keys)[:room])
            related_nodes = Node.search(
                [("snapshot_id", "=", snapshot.id), ("node_key", "in", list(next_keys))],
                order="node_type, label, id",
            )
            for node in related_nodes:
                nodes_by_key[node.node_key] = node
            frontier = set(nodes_by_key).intersection(next_keys)

        nodes = list(nodes_by_key.values())
        keys = set(nodes_by_key)
        edges = [
            edge for edge in edge_by_key.values()
            if edge.source_key in keys and edge.target_key in keys
        ][: self.EDGE_LIMIT]
        return {
            "nodes": [self._node_payload(node) for node in nodes],
            "edges": [self._edge_payload(edge) for edge in edges],
            "budget_exceeded": budget_exceeded,
            "needs_focus": False,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "rendered_nodes": len(nodes),
            "rendered_edges": len(edges),
            "render_limits": {"nodes": self.NODE_LIMIT, "edges": self.EDGE_LIMIT},
        }

    @staticmethod
    def _model_keys_for_permission(snapshot, permission, Node, Edge):
        """Return models reached by ACLs granting the requested CRUD mode."""
        permission_field = {
            "read": "perm_read",
            "write": "perm_write",
            "create": "perm_create",
            "delete": "perm_unlink",
        }.get(permission)
        if not permission_field:
            return set()
        acl_nodes = Node.search([("snapshot_id", "=", snapshot.id), ("node_type", "=", "acl")])
        acl_keys = {
            node.node_key for node in acl_nodes
            if bool((node.metadata_json or {}).get(permission_field))
        }
        if not acl_keys:
            return set()
        edges = Edge.search([
            ("snapshot_id", "=", snapshot.id),
            ("source_key", "in", list(acl_keys)),
            ("edge_type", "=", "protects"),
        ])
        return set(edges.mapped("target_key"))

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
        related_keys = {
            edge.source_key if edge.target_key == node_key else edge.target_key
            for edge in edges
        }
        related_nodes = Node.search(
            [("snapshot_id", "=", snapshot.id), ("node_key", "in", list(related_keys))]
        ) if related_keys else Node.browse()
        related_by_key = {related.node_key: related for related in related_nodes}
        relationships = []
        access_sources = []
        access_summary = {"read": False, "write": False, "create": False, "delete": False}
        for edge in edges:
            related_key = edge.source_key if edge.target_key == node_key else edge.target_key
            related = related_by_key.get(related_key)
            if not related:
                continue
            related_payload = self._node_payload(related)
            relationships.append({
                "edge_type": edge.edge_type,
                "direction": "incoming" if edge.target_key == node_key else "outgoing",
                "node": related_payload,
                "metadata": edge.metadata_json or {},
            })
            if related.node_type == "acl" or node.node_type == "acl":
                metadata = related.metadata_json if related.node_type == "acl" else node.metadata_json
                access_summary["read"] |= bool(metadata.get("perm_read"))
                access_summary["write"] |= bool(metadata.get("perm_write"))
                access_summary["create"] |= bool(metadata.get("perm_create"))
                access_summary["delete"] |= bool(metadata.get("perm_unlink"))
                if related.node_type == "acl":
                    access_sources.append(related_payload)
        access_summary["sources"] = access_sources
        access_summary["rule_count"] = sum(
            1 for relationship in relationships if relationship["node"]["type"] == "rule"
        )
        return {
            "node": self._node_payload(node),
            "edges": [self._edge_payload(edge) for edge in edges],
            "relationships": relationships,
            "access_summary": access_summary,
        }

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

    def compare_snapshots(self, current, baseline):
        """Return a read-only, bounded diff between two completed snapshots."""
        Node = self.env["oav.access.snapshot.node"].sudo()
        Edge = self.env["oav.access.snapshot.edge"].sudo()
        Finding = self.env["oav.access.finding"].sudo()

        def stable(value):
            return json.dumps(value or {}, sort_keys=True, default=str)

        current_nodes = {node.node_key: node for node in Node.search([("snapshot_id", "=", current.id)])}
        baseline_nodes = {node.node_key: node for node in Node.search([("snapshot_id", "=", baseline.id)])}
        current_edges = {self._edge_payload(edge)["id"]: edge for edge in Edge.search([("snapshot_id", "=", current.id)])}
        baseline_edges = {self._edge_payload(edge)["id"]: edge for edge in Edge.search([("snapshot_id", "=", baseline.id)])}
        current_findings = {finding.fingerprint or f"{finding.finding_type}:{finding.title}": finding for finding in Finding.search([("snapshot_id", "=", current.id)])}
        baseline_findings = {finding.fingerprint or f"{finding.finding_type}:{finding.title}": finding for finding in Finding.search([("snapshot_id", "=", baseline.id)])}

        def diff_records(current_map, baseline_map, payload):
            added = [payload(current_map[key]) for key in current_map.keys() - baseline_map.keys()]
            removed = [payload(baseline_map[key]) for key in baseline_map.keys() - current_map.keys()]
            changed = []
            for key in current_map.keys() & baseline_map.keys():
                current_value, baseline_value = payload(current_map[key]), payload(baseline_map[key])
                if stable(current_value) != stable(baseline_value):
                    changed.append({"key": key, "current": current_value, "baseline": baseline_value})
            return {"added": added, "removed": removed, "changed": changed}

        def finding_payload(finding):
            return {
                "fingerprint": finding.fingerprint or f"{finding.finding_type}:{finding.title}",
                "type": finding.finding_type,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "model_name": finding.model_name or "",
            }

        nodes = diff_records(current_nodes, baseline_nodes, self._node_payload)
        edges = diff_records(current_edges, baseline_edges, self._edge_payload)
        findings = diff_records(current_findings, baseline_findings, finding_payload)
        return {
            "baseline": baseline._status_payload(),
            "current": current._status_payload(),
            "summary": {
                "nodes_added": len(nodes["added"]), "nodes_removed": len(nodes["removed"]), "nodes_changed": len(nodes["changed"]),
                "edges_added": len(edges["added"]), "edges_removed": len(edges["removed"]), "edges_changed": len(edges["changed"]),
                "findings_added": len(findings["added"]), "findings_removed": len(findings["removed"]), "findings_changed": len(findings["changed"]),
            },
            "nodes": nodes,
            "edges": edges,
            "findings": findings,
        }

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
        layer_rows = Node._read_group(
            [("snapshot_id", "=", snapshot.id)], ["node_type"], ["__count"]
        )
        layer_counts = {node_type: count for node_type, count in layer_rows if node_type}
        layers = [
            {"type": node_type, "label": label, "count": layer_counts.get(node_type, 0)}
            for node_type, label in self.NODE_LABELS.items()
        ]
        severity_rows = Finding._read_group(
            [("snapshot_id", "=", snapshot.id)], ["severity"], ["__count"]
        )
        severity_counts = {severity: count for severity, count in severity_rows if severity}
        type_rows = Finding._read_group(
            [("snapshot_id", "=", snapshot.id)], ["finding_type"], ["__count"]
        )
        finding_type_counts = [
            {
                "type": finding_type,
                "label": self.FINDING_LABELS.get(finding_type, finding_type),
                "count": count,
            }
            for finding_type, count in type_rows
            if finding_type
        ]
        return {
            "layers": layers,
            "severity_counts": severity_counts,
            "finding_type_counts": sorted(
                finding_type_counts, key=lambda row: row["count"], reverse=True
            ),
            "top_findings": self.get_findings(snapshot, {"limit": 5}),
        }

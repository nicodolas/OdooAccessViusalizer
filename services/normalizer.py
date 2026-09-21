from collections import defaultdict


class AccessSnapshotNormalizer:
    """Build compact, stable graph records from Odoo security records."""

    NODE_TYPES = {
        "category",
        "privilege",
        "user",
        "group",
        "model",
        "acl",
        "rule",
        "menu",
    }

    def __init__(self, env):
        self.env = env
        self.nodes = {}
        self.edges = {}
        self.provenance = defaultdict(dict)

    @staticmethod
    def key(node_type, model, record_id):
        return f"{node_type}:{model}:{record_id}"

    def load_provenance(self, model, ids):
        ids = list({record_id for record_id in ids if record_id})
        if not ids:
            return
        self.env.cr.execute(
            """
            SELECT res_id, module, name
              FROM ir_model_data
             WHERE model = %s AND res_id = ANY(%s)
            """,
            (model, ids),
        )
        self.provenance[model].update(
            {res_id: {"module": module, "name": name} for res_id, module, name in self.env.cr.fetchall()}
        )

    def module_for(self, model, record_id):
        return self.provenance[model].get(record_id, {}).get("module") or "unknown"

    def add_node(
        self,
        node_type,
        record,
        label=None,
        technical_name=None,
        module=None,
        category=None,
        metadata=None,
    ):
        if node_type not in self.NODE_TYPES:
            raise ValueError(f"Unknown node type: {node_type}")
        source_model = record._name if record else False
        source_id = record.id if record else False
        node_key = self.key(node_type, source_model, source_id)
        label = str(label or getattr(record, "display_name", False) or record)
        metadata = metadata or {}
        values = {
            "node_key": node_key,
            "node_type": node_type,
            "source_model": source_model,
            "source_id": source_id,
            "module": module or self.module_for(source_model, source_id),
            "category": category or False,
            "label": label,
            "technical_name": technical_name or False,
            "search_text": " ".join(
                str(value)
                for value in (label, technical_name, module, category)
                if value
            ).lower(),
            "metadata_json": metadata,
        }
        self.nodes[node_key] = values
        return node_key

    def add_edge(self, source_key, target_key, edge_type, label=None, metadata=None):
        edge_key = (source_key, target_key, edge_type)
        if edge_key not in self.edges:
            self.edges[edge_key] = {
                "source_key": source_key,
                "target_key": target_key,
                "edge_type": edge_type,
                "label": label or False,
                "metadata_json": metadata or {},
            }


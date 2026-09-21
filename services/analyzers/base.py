import hashlib
import json


class FindingBuilder:
    def __init__(self):
        self.findings = []
        self._fingerprints = set()

    def add(
        self,
        finding_type,
        severity,
        certainty,
        title,
        description,
        recommendation,
        model_name=None,
        evidence=None,
        node_keys=None,
        edge_keys=None,
    ):
        evidence = evidence or {}
        node_keys = sorted(set(node_keys or []))
        edge_keys = sorted(set(edge_keys or []))
        fingerprint_data = {
            "finding_type": finding_type,
            "model_name": model_name,
            "evidence": evidence,
            "node_keys": node_keys,
            "edge_keys": edge_keys,
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        if fingerprint in self._fingerprints:
            return
        self._fingerprints.add(fingerprint)
        self.findings.append(
            {
                "finding_type": finding_type,
                "severity": severity,
                "certainty": certainty,
                "title": title,
                "description": description,
                "recommendation": recommendation,
                "model_name": model_name or False,
                "evidence_json": evidence,
                "affected_node_keys": node_keys,
                "affected_edge_keys": edge_keys,
                "fingerprint": fingerprint,
            }
        )


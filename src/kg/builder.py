"""Neo4j knowledge graph builder with PageRank and Pearson analysis."""
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import pearsonr


class KnowledgeGraphBuilder:
    """Build and analyze a technical indicator knowledge graph."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or "bolt://localhost:7687"
        self.user = user or "neo4j"
        self.password = password or "neo4j"
        self._driver = None
        # In-memory storage for offline analysis
        self.nodes: Dict[str, dict] = {}
        self.edges: List[Tuple[str, str, str]] = []  # (from, to, relation)
        self.indicator_values: Dict[str, List[float]] = defaultdict(list)

    def add_patent(self, patent_id: str, title: str = "", date: str = ""):
        """Add a patent node."""
        self.nodes[patent_id] = {
            "type": "Patent",
            "id": patent_id,
            "title": title,
            "date": date,
        }

    def add_indicator(
        self,
        patent_id: str,
        quintuple_dict: dict,
    ):
        """Add an indicator node and connect to patent."""
        ind_id = f"IND-{len(self.nodes):06d}"
        name = quintuple_dict.get("指标名称", "")
        value = quintuple_dict.get("指标数值", "")
        relation = quintuple_dict.get("指标关系", "")
        obj = quintuple_dict.get("指标对象", "")
        condition = quintuple_dict.get("实验条件", "")

        # Indicator node
        self.nodes[ind_id] = {
            "type": "TechnicalIndicator",
            "id": ind_id,
            "name": name,
            "value": value,
            "relation": relation,
            "object": obj,
            "condition": condition,
            "category": _classify(name),
        }

        # Edges
        self.edges.append((patent_id, ind_id, "HAS_INDICATOR"))

        # Track numeric values for Pearson
        numeric_val = _extract_numeric(value)
        if numeric_val is not None:
            self.indicator_values[name].append(numeric_val)

    def build_from_records(
        self,
        records: List[dict],
        limit: int = 0,
    ):
        """Build KG from extraction records."""
        count = 0
        for record in records:
            patent_id = record.get("patent_id", f"PAT-{count:06d}")
            self.add_patent(
                patent_id,
                title=record.get("input", "")[:100],
            )

            output = record.get("output", "")
            try:
                quints = json.loads(output) if isinstance(output, str) else output
                if isinstance(quints, dict):
                    quints = [quints]
                for q in quints:
                    self.add_indicator(patent_id, q)
                    count += 1
                    if limit and count >= limit:
                        break
            except (json.JSONDecodeError, TypeError):
                pass

            if limit and count >= limit:
                break

    def compute_pagerank(
        self,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> Dict[str, float]:
        """Compute PageRank on the knowledge graph.

        Returns:
            Dict mapping node_id -> PageRank score
        """
        # Build adjacency
        adj = defaultdict(set)
        all_nodes = set(self.nodes.keys())

        for from_id, to_id, _ in self.edges:
            adj[from_id].add(to_id)
            all_nodes.add(from_id)
            all_nodes.add(to_id)

        n = len(all_nodes)
        if n == 0:
            return {}

        node_list = sorted(all_nodes)
        node_index = {node: i for i, node in enumerate(node_list)}

        # Initialize
        pr = np.ones(n) / n

        # Build transition matrix as sparse adjacency
        for iteration in range(max_iter):
            new_pr = np.ones(n) * (1 - damping) / n

            for from_id, to_ids in adj.items():
                if not to_ids:
                    continue
                fi = node_index[from_id]
                for to_id in to_ids:
                    ti = node_index[to_id]
                    new_pr[ti] += damping * pr[fi] / len(to_ids)

            # Handle dangling nodes
            dangling = np.sum(pr) - np.sum(
                [pr[node_index[n]] for n in node_list if adj[n]]
            )
            new_pr += damping * dangling / n

            diff = np.sum(np.abs(new_pr - pr))
            pr = new_pr

            if diff < tol:
                break

        return {node: float(pr[node_index[node]]) for node in node_list}

    def compute_pearson_correlations(
        self, min_cooccurrence: int = 3
    ) -> List[dict]:
        """Compute Pearson correlations between indicator pairs.

        Returns:
            List of {indicator_a, indicator_b, correlation, p_value, n}
        """
        names = list(self.indicator_values.keys())
        results = []

        for i, name_a in enumerate(names):
            for name_b in names[i + 1 :]:
                vals_a = self.indicator_values[name_a]
                vals_b = self.indicator_values[name_b]

                # Align by same-length samples
                min_len = min(len(vals_a), len(vals_b))
                if min_len < min_cooccurrence:
                    continue

                try:
                    corr, p_value = pearsonr(vals_a[:min_len], vals_b[:min_len])
                    if not math.isnan(corr):
                        results.append({
                            "indicator_a": name_a,
                            "indicator_b": name_b,
                            "correlation": float(corr),
                            "p_value": float(p_value),
                            "n": min_len,
                        })
                except Exception:
                    continue

        results.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return results

    def get_stats(self) -> dict:
        """Return graph statistics."""
        patent_count = sum(
            1 for n in self.nodes.values() if n["type"] == "Patent"
        )
        indicator_count = sum(
            1 for n in self.nodes.values()
            if n["type"] == "TechnicalIndicator"
        )
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "patents": patent_count,
            "indicators": indicator_count,
            "unique_indicators": len(self.indicator_values),
            "edge_type_distribution": {
                rel: sum(1 for _, _, r in self.edges if r == rel)
                for rel in set(r for _, _, r in self.edges)
            },
        }

    def export_to_neo4j_cypher(self, output_path: str) -> str:
        """Export the graph as Cypher statements for Neo4j import."""
        lines = []

        # Create nodes
        for node_id, props in self.nodes.items():
            label = props["type"]
            props_str = ", ".join(
                f"{k}: {_escape_value(v)}"
                for k, v in props.items()
                if k != "type"
            )
            lines.append(
                f"CREATE (:{label} {{id: {_escape_value(node_id)}, {props_str}}});"
            )

        # Create edges
        for from_id, to_id, rel_type in self.edges:
            lines.append(f"""
MATCH (a {{id: {_escape_value(from_id)}}}), (b {{id: {_escape_value(to_id)}}})
CREATE (a)-[:{rel_type}]->(b);
""".strip())

        cypher = "\n".join(lines)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cypher)

        return cypher

    def to_jsonld(self, output_path: str = None) -> dict:
        """Export as JSON-LD for semantic web interoperability."""
        from kg.ontology import JSONLD_CONTEXT

        graph = {"@context": JSONLD_CONTEXT["@context"], "@graph": []}

        for node_id, props in self.nodes.items():
            entry = {
                "@id": f"http://example.org/{props['type'].lower()}/{node_id}",
                "@type": props["type"],
                **{k: v for k, v in props.items() if k not in ("type", "id")},
            }
            graph["@graph"].append(entry)

        for from_id, to_id, rel in self.edges:
            graph["@graph"].append({
                "@id": f"http://example.org/relation/{from_id}-{to_id}",
                "subject": f"http://example.org/{self.nodes[from_id]['type'].lower()}/{from_id}",
                "predicate": rel,
                "object": f"http://example.org/{self.nodes[to_id]['type'].lower()}/{to_id}",
            })

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(graph, f, ensure_ascii=False, indent=2)

        return graph


def _classify(name: str) -> str:
    """Classify indicator name into category."""
    categories = {
        "电化学性能": ["比容量", "能量密度", "功率密度", "循环", "库伦", "倍率", "放电", "充电"],
        "物理特性": ["密度", "比表面积", "粒度", "粒径", "厚度", "孔隙率"],
        "热力学": ["温度", "热稳定", "分解", "熔点", "玻璃化"],
        "力学性能": ["强度", "断裂", "弹性", "硬度"],
        "工艺参数": ["烧结", "保温", "升温", "降温", "质量分数", "浓度", "粘度", "固含量"],
        "电学特性": ["电导", "电化学窗口", "电压", "阻抗", "扩散系数", "迁移数"],
    }
    for category, keywords in categories.items():
        if any(kw in name for kw in keywords):
            return category
    return "其他"


def _extract_numeric(value: str) -> Optional[float]:
    """Extract numeric value from a value string like '300Wh/kg'."""
    import re

    nums = re.findall(r"\d+\.?\d*", str(value))
    if nums:
        return float(nums[0])
    return None


def _escape_value(v) -> str:
    """Escape a value for Cypher."""
    if isinstance(v, (int, float)):
        return str(v)
    return f"'{str(v).replace(chr(39), chr(39)*2)}'"

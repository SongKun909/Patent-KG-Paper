"""Knowledge graph service: Neo4j + pyvis."""
from typing import Optional

from neo4j import GraphDatabase

from app.config import settings


class KGService:
    """Neo4j graph query + pyvis visualization service."""

    def __init__(self):
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    def query(self, cypher: str, params: dict = None) -> list:
        """Execute a Cypher query and return results."""
        with self.driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def search_indicators(self, keyword: str, limit: int = 50) -> list:
        """Search for indicators by keyword."""
        cypher = """
            MATCH (p:Patent)-[:HAS_INDICATOR]->(i:TechnicalIndicator)
            WHERE i.name CONTAINS $keyword OR i.object CONTAINS $keyword
            RETURN p.id AS patent_id, i.name AS name, i.value AS value,
                   i.object AS object, i.condition AS condition
            LIMIT $limit
        """
        return self.query(cypher, {"keyword": keyword, "limit": limit})

    def get_pagerank(self, limit: int = 20) -> list:
        """Get top nodes by PageRank."""
        cypher = """
            CALL gds.pageRank.stream('indicatorGraph')
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE node:TechnicalIndicator
            RETURN node.name AS name, node.value AS value, score
            ORDER BY score DESC
            LIMIT $limit
        """
        try:
            return self.query(cypher, {"limit": limit})
        except Exception:
            # Fallback: simple degree-based ranking
            cypher = """
                MATCH (i:TechnicalIndicator)-[r]-()
                RETURN i.name AS name, i.value AS value,
                       count(r) AS score
                ORDER BY score DESC
                LIMIT $limit
            """
            return self.query(cypher, {"limit": limit})

    def get_pearson_pairs(self, limit: int = 20) -> list:
        """Get indicator pairs with CORRELATED_WITH relationships."""
        cypher = """
            MATCH (a:TechnicalIndicator)-[c:CORRELATED_WITH]->(b:TechnicalIndicator)
            RETURN a.name AS ind_a, a.value AS val_a,
                   b.name AS ind_b, b.value AS val_b,
                   c.strength AS correlation
            ORDER BY abs(c.strength) DESC
            LIMIT $limit
        """
        return self.query(cypher, {"limit": limit})

    def generate_pyvis_html(self, keyword: str = None, limit: int = 100) -> str:
        """Generate an interactive pyvis network HTML string."""
        try:
            from pyvis.network import Network

            net = Network(height="700px", width="100%", bgcolor="#1a1a2e", font_color="white")
            net.set_options("""
            {
              "nodes": {"borderWidth": 2, "borderWidthSelected": 4},
              "edges": {"color": {"inherit": true}, "smooth": false},
              "physics": {"barnesHut": {"gravitationalConstant": -2000, "springLength": 250}}
            }
            """)

            # Query nodes from Neo4j
            if keyword:
                cypher = """
                    MATCH (p:Patent)-[:HAS_INDICATOR]->(i:TechnicalIndicator)
                    WHERE i.name CONTAINS $keyword OR i.object CONTAINS $keyword
                    RETURN p, i LIMIT $limit
                """
            else:
                cypher = """
                    MATCH (p:Patent)-[:HAS_INDICATOR]->(i:TechnicalIndicator)
                    RETURN p, i LIMIT $limit
                """

            with self.driver.session() as session:
                result = session.run(cypher, {"keyword": keyword or "", "limit": limit})
                added_patents = set()
                added_indicators = set()
                for record in result:
                    p = record["p"]
                    i = record["i"]
                    pid = p.get("id", "")
                    if pid not in added_patents:
                        net.add_node(pid, label=f"Patent: {pid[:12]}", color="#4fc3f7", shape="box")
                        added_patents.add(pid)
                    iid = i.get("name", "") + "_" + str(i.get("value", ""))
                    if iid not in added_indicators:
                        label = i.get("name", "")[:20]
                        if i.get("value"):
                            label += f"\n{i.get('value', '')}"
                        net.add_node(iid, label=label, color="#ff8a65", shape="ellipse")
                        added_indicators.add(iid)
                    net.add_edge(pid, iid, color="#64b5f6")

            return net.generate_html()
        except ImportError:
            return "<p style='color:red'>pyvis not installed. Run: pip install pyvis</p>"
        except Exception as e:
            return f"<p style='color:red'>Error generating graph: {e}</p>"


kg_service = KGService()

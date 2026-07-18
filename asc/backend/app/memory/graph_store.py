"""Neo4j-backed knowledge graph for memory relationships.

Records memory nodes and ``RELATED_TO`` edges so agents can traverse related
context. Keeps an in-process adjacency mirror so ``related()`` works even when
Neo4j is not deployed (dev/tests), degrading gracefully.
"""

import logging
from collections import defaultdict
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("asc.memory.graph")


class GraphStore:
    """Knowledge graph over memory entries with in-memory fallback."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        self._driver = None
        self._available = False
        # In-memory adjacency: node_id -> set of related node_ids
        self._edges: dict[str, set[str]] = defaultdict(set)
        self._nodes: dict[str, dict] = {}

        should_connect = settings.GRAPH_ENABLED if enabled is None else enabled
        if should_connect:
            self._connect(
                uri or settings.NEO4J_URI,
                user or settings.NEO4J_USER,
                password or settings.NEO4J_PASSWORD,
            )

    def _connect(self, uri: str, user: str, password: str) -> None:
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            self._available = True
            logger.info("Neo4j connected at %s", uri)
        except Exception as exc:  # noqa: BLE001 - fall back to in-memory graph
            self._driver = None
            self._available = False
            logger.warning("Neo4j unavailable, using in-memory graph: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    def add_node(self, node_id: str, content: str = "", tier: str = "") -> None:
        self._nodes[node_id] = {"content": content, "tier": tier}
        if not self._available:
            return
        try:
            with self._driver.session() as session:
                session.run(
                    "MERGE (m:Memory {id: $id}) "
                    "SET m.content = $content, m.tier = $tier",
                    id=node_id, content=content, tier=tier,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Neo4j add_node failed: %s", exc)

    def add_relationship(self, from_id: str, to_id: str) -> None:
        """Create an undirected relationship between two memory nodes."""
        self._edges[from_id].add(to_id)
        self._edges[to_id].add(from_id)
        if not self._available:
            return
        try:
            with self._driver.session() as session:
                session.run(
                    "MERGE (a:Memory {id: $a}) "
                    "MERGE (b:Memory {id: $b}) "
                    "MERGE (a)-[:RELATED_TO]->(b)",
                    a=from_id, b=to_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Neo4j add_relationship failed: %s", exc)

    def related(self, node_id: str, limit: int = 10) -> list[str]:
        """Return ids related to ``node_id``."""
        if self._available:
            try:
                with self._driver.session() as session:
                    result = session.run(
                        "MATCH (m:Memory {id: $id})-[:RELATED_TO]-(n:Memory) "
                        "RETURN n.id AS id LIMIT $limit",
                        id=node_id, limit=limit,
                    )
                    ids = [record["id"] for record in result]
                    if ids:
                        return ids
            except Exception as exc:  # noqa: BLE001
                logger.warning("Neo4j related query failed: %s", exc)
        return list(self._edges.get(node_id, set()))[:limit]

    def close(self) -> None:
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:  # noqa: BLE001
                pass

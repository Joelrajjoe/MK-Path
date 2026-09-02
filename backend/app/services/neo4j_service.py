import logging
from typing import Dict, Any, List, Optional, Tuple
from neo4j import GraphDatabase
from ..config import settings

logger = logging.getLogger("mkpath.neo4j")

class Neo4jService:
    def __init__(self):
        self.driver = None
        self.is_available = False
        
        # Local in-memory graph backup (scoping by clerk_user_id for strict user isolation)
        self.in_memory_nodes: Dict[str, Dict[str, Dict[str, Any]]] = {}  # clerk_id -> concept_name -> properties
        self.in_memory_edges: Dict[str, List[Dict[str, Any]]] = {}       # clerk_id -> list of edges (source, target, type)
        
        self.initialize_driver()

    def initialize_driver(self):
        uri = settings.NEO4J_URI
        username = settings.NEO4J_USERNAME
        password = settings.NEO4J_PASSWORD
        
        if not uri or not password:
            logger.warning("Neo4j settings are incomplete in .env. Graph computation is running in in-memory local fallback mode.")
            self.is_available = False
            return

        try:
            # Short connection timeouts so backend startup is fast if offline
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(username, password),
                connection_timeout=2.0,
                max_connection_lifetime=30.0
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            self.is_available = True
            logger.info("Successfully connected to Neo4j Graph Database!")
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j at {uri}: {e}. Running in in-memory local fallback mode.")
            self.is_available = False
            if self.driver:
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    # --- Core Synchronization Layer ---

    async def sync_concept(self, clerk_user_id: str, concept: Dict[str, Any]):
        """Merges concept node properties into Neo4j, falling back to local memory if offline."""
        c_name = concept.get("name")
        c_id = str(concept.get("_id") or concept.get("concept_id", ""))
        properties = {
            "concept_id": c_id,
            "name": c_name,
            "difficulty": concept.get("difficulty", "basic"),
            "exam_relevance": float(concept.get("exam_relevance", 0)),
            "industry_relevance": float(concept.get("industry_relevance", 0))
        }

        # Local in-memory sync always happens (ensuring fallback state remains hot)
        if clerk_user_id not in self.in_memory_nodes:
            self.in_memory_nodes[clerk_user_id] = {}
        self.in_memory_nodes[clerk_user_id][c_name] = properties

        if not self.is_available or not self.driver:
            return

        try:
            def _merge_node(tx, c_user_id, props):
                tx.run(
                    "MERGE (c:Concept {clerk_user_id: $clerk_user_id, name: $name}) "
                    "SET c.concept_id = $concept_id, "
                    "    c.difficulty = $difficulty, "
                    "    c.exam_relevance = $exam_relevance, "
                    "    c.industry_relevance = $industry_relevance",
                    clerk_user_id=c_user_id,
                    concept_id=props["concept_id"],
                    name=props["name"],
                    difficulty=props["difficulty"],
                    exam_relevance=props["exam_relevance"],
                    industry_relevance=props["industry_relevance"]
                )
            
            with self.driver.session() as session:
                session.execute_write(_merge_node, clerk_user_id, properties)
        except Exception as e:
            logger.error(f"Neo4j concept sync failed: {e}. Falling back to memory storage.")

    async def sync_relationship(self, clerk_user_id: str, relationship: Dict[str, Any]):
        """Creates relationship edges between Concept nodes in Neo4j, falling back to local memory if offline."""
        src = relationship.get("source_concept_name")
        dst = relationship.get("target_concept_name")
        rel_type = relationship.get("relationship_type", "PREREQUISITE_OF").upper()

        if rel_type == "PREREQUISITE":
            rel_type = "PREREQUISITE_OF"

        edge = {"source": src, "target": dst, "type": rel_type}

        # Local in-memory sync
        if clerk_user_id not in self.in_memory_edges:
            self.in_memory_edges[clerk_user_id] = []
        # Avoid duplicate edges
        if edge not in self.in_memory_edges[clerk_user_id]:
            self.in_memory_edges[clerk_user_id].append(edge)

        if not self.is_available or not self.driver:
            return

        try:
            def _create_edge(tx, c_user_id, source, target, r_type):
                # Using APOC or Cypher concatenation to dynamically set relationship type labels
                tx.run(
                    f"MATCH (a:Concept {{clerk_user_id: $clerk_user_id, name: $source}}) "
                    f"MATCH (b:Concept {{clerk_user_id: $clerk_user_id, name: $target}}) "
                    f"MERGE (a)-[r:{r_type}]->(b)",
                    clerk_user_id=c_user_id,
                    source=source,
                    target=target
                )
            
            with self.driver.session() as session:
                session.execute_write(_create_edge, clerk_user_id, src, dst, rel_type)
        except Exception as e:
            logger.error(f"Neo4j relationship sync failed: {e}. Falling back to memory storage.")

    # --- Graph Intelligence Analytics Layer ---

    async def get_prerequisites(self, clerk_user_id: str, concept_name: str) -> List[str]:
        """Returns concepts that are direct prerequisites of the given concept."""
        if self.is_available and self.driver:
            try:
                def _query(tx, c_user_id, c_name):
                    res = tx.run(
                        "MATCH (p:Concept {clerk_user_id: $clerk_user_id})-[:PREREQUISITE_OF]->(c:Concept {clerk_user_id: $clerk_user_id, name: $name}) "
                        "RETURN p.name as name",
                        clerk_user_id=c_user_id,
                        name=c_name
                    )
                    return [r["name"] for r in res]
                
                with self.driver.session() as session:
                    return session.execute_read(_query, clerk_user_id, concept_name)
            except Exception as e:
                logger.error(f"Neo4j get_prerequisites failed: {e}. Falling back to memory.")

        # Local traversal fallback
        edges = self.in_memory_edges.get(clerk_user_id, [])
        return [edge["source"] for edge in edges if edge["target"] == concept_name and edge["type"] == "PREREQUISITE_OF"]

    async def get_dependents(self, clerk_user_id: str, concept_name: str) -> List[str]:
        """Returns concepts that depend on the given concept (i.e. this concept is their prerequisite)."""
        if self.is_available and self.driver:
            try:
                def _query(tx, c_user_id, c_name):
                    res = tx.run(
                        "MATCH (c:Concept {clerk_user_id: $clerk_user_id, name: $name})-[:PREREQUISITE_OF]->(d:Concept {clerk_user_id: $clerk_user_id}) "
                        "RETURN d.name as name",
                        clerk_user_id=c_user_id,
                        name=c_name
                    )
                    return [r["name"] for r in res]
                
                with self.driver.session() as session:
                    return session.execute_read(_query, clerk_user_id, concept_name)
            except Exception as e:
                logger.error(f"Neo4j get_dependents failed: {e}. Falling back to memory.")

        edges = self.in_memory_edges.get(clerk_user_id, [])
        return [edge["target"] for edge in edges if edge["source"] == concept_name and edge["type"] == "PREREQUISITE_OF"]

    async def shortest_prerequisite_path(self, clerk_user_id: str, source: str, target: str) -> List[str]:
        """Calculates the shortest prerequisite path between source and target concepts."""
        if self.is_available and self.driver:
            try:
                def _query(tx, c_user_id, src, dst):
                    res = tx.run(
                        "MATCH p = shortestPath((a:Concept {clerk_user_id: $clerk_user_id, name: $src})-[:PREREQUISITE_OF*]->(b:Concept {clerk_user_id: $clerk_user_id, name: $dst})) "
                        "RETURN [n in nodes(p) | n.name] as path",
                        clerk_user_id=c_user_id,
                        src=src,
                        dst=dst
                    )
                    record = res.single()
                    return record["path"] if record else []
                
                with self.driver.session() as session:
                    return session.execute_read(_query, clerk_user_id, source, target)
            except Exception as e:
                logger.error(f"Neo4j shortestPath failed: {e}. Falling back to BFS.")

        # In-memory BFS shortest path
        edges = self.in_memory_edges.get(clerk_user_id, [])
        adj = {}
        for edge in edges:
            if edge["type"] == "PREREQUISITE_OF":
                s = edge["source"]
                t = edge["target"]
                if s not in adj:
                    adj[s] = []
                adj[s].append(t)
        
        # BFS search
        queue = [[source]]
        visited = {source}
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == target:
                return path
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(neighbor)
                    queue.append(new_path)
        return []

    async def prerequisite_depth(self, clerk_user_id: str, concept_name: str) -> int:
        """Returns the prerequisite depth of a concept (length of longest prerequisite chain up to it)."""
        # BFS depth tracing
        edges = self.in_memory_edges.get(clerk_user_id, [])
        # We find all nodes that lead to concept_name recursively
        memo = {}
        
        def get_depth(node):
            if node in memo:
                return memo[node]
            prereqs = [edge["source"] for edge in edges if edge["target"] == node and edge["type"] == "PREREQUISITE_OF"]
            if not prereqs:
                return 0
            max_depth = 1 + max(get_depth(p) for p in prereqs)
            memo[node] = max_depth
            return max_depth
            
        return get_depth(concept_name)

    async def get_neighborhood(self, clerk_user_id: str, concept_name: str) -> List[str]:
        """Returns neighbor concepts directly connected by any edge type (prerequisite, related, part_of)."""
        if self.is_available and self.driver:
            try:
                def _query(tx, c_user_id, c_name):
                    res = tx.run(
                        "MATCH (c:Concept {clerk_user_id: $clerk_user_id, name: $name})-[r]-(n:Concept {clerk_user_id: $clerk_user_id}) "
                        "RETURN DISTINCT n.name as name",
                        clerk_user_id=c_user_id,
                        name=c_name
                    )
                    return [r["name"] for r in res]
                
                with self.driver.session() as session:
                    return session.execute_read(_query, clerk_user_id, concept_name)
            except Exception as e:
                logger.error(f"Neo4j get_neighborhood failed: {e}. Falling back to memory.")

        edges = self.in_memory_edges.get(clerk_user_id, [])
        neighbors = set()
        for edge in edges:
            if edge["source"] == concept_name:
                neighbors.add(edge["target"])
            elif edge["target"] == concept_name:
                neighbors.add(edge["source"])
        return list(neighbors)

    async def concept_centrality(self, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Calculates centrality of concepts based on node connection degree, sorted by weight."""
        nodes = self.in_memory_nodes.get(clerk_user_id, {})
        edges = self.in_memory_edges.get(clerk_user_id, [])
        
        if not nodes:
            return []

        degree = {name: 0 for name in nodes.keys()}
        for edge in edges:
            s = edge["source"]
            t = edge["target"]
            if s in degree:
                degree[s] += 1
            if t in degree:
                degree[t] += 1

        total_nodes = len(nodes)
        centrality_list = []
        for name, deg in degree.items():
            norm_centrality = deg / (total_nodes - 1) if total_nodes > 1 else 0.0
            centrality_list.append({
                "concept_name": name,
                "degree": deg,
                "centrality": round(norm_centrality, 4)
            })

        centrality_list.sort(key=lambda x: x["centrality"], reverse=True)
        return centrality_list

# Instantiate a global singleton service
neo4j_service = Neo4jService()

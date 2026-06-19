import os
import sys
import asyncio
import logging

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.deep_search import DeepSearchService
from app.services.graph_builder import GraphBuilderService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_deep_search():
    logger.info("=== Testing Deep Search (Anti-Data Leakage) ===")
    search = DeepSearchService()
    # Test with cutoff date
    theme = "Argentina inflation rate 2024"
    max_date = "2023-12-31"
    
    logger.info(f"Querying: {theme} with Cutoff: {max_date}")
    result = search.perform_research(theme, max_results=2, max_date=max_date)
    logger.info("\n--- Deep Search Result ---")
    logger.info(result[:1500] + "...\n")
    
def test_deduplication():
    logger.info("=== Testing Graph Deduplication ===")
    builder = GraphBuilderService()
    
    # 1. Create a graph
    graph_id = builder.create_graph("S3 Deduplication Test Graph")
    logger.info(f"Created Graph: {graph_id}")
    
    # 2. Ontology definition
    ontology = {
        "entity_types": [
            {"name": "Person", "description": "A human being"},
            {"name": "Concept", "description": "An abstract idea"}
        ],
        "edge_types": [
            {
                "name": "Knows", 
                "description": "Knows someone",
                "source_targets": [{"source": "Person", "target": "Person"}]
            }
        ]
    }
    builder.set_ontology(graph_id, ontology)
    
    # 3. Add text with clear duplication
    text = """
    John is a data scientist. He works in Buenos Aires.
    Juan is a data scientist. He works in Buenos Aires.
    Johnny is a data scientist. He works in Buenos Aires.
    Alice knows John. Alice is a manager.
    """
    logger.info("Adding text to trigger graph generation and deduplication...")
    
    # Run deduplication flow directly using add_text_batches
    episode_uuids = builder.add_text_batches(graph_id, [text], batch_size=1)
    
    logger.info("Waiting for Graphiti to process episodes...")
    builder._wait_for_episodes(graph_id, episode_uuids)
    
    import time
    logger.info("Waiting 10s for Neo4j to index the graph...")
    time.sleep(10)
    
    # Print Graph Data
    data = builder.get_graph_data(graph_id)
    logger.info("\n--- Resulting Nodes ---")
    for n in data["nodes"]:
        logger.info(f"Node: {n['name']} (UUID: {n['uuid']})")
        
    logger.info("\n--- Resulting Edges ---")
    for e in data["edges"]:
        logger.info(f"Edge: {e['source_node_name']} --[{e['fact_type']}]--> {e['target_node_name']}")
        
    # Clean up
    builder.delete_graph(graph_id)
    logger.info("Test graph deleted.")

if __name__ == "__main__":
    test_deep_search()
    test_deduplication()

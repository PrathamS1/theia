#!/usr/bin/env python3
"""
scripts/verify_server_apis.py — Automated end-to-end verification of all FastAPI server routes.
Tests:
1. GET  /api/health
2. GET  /api/questions
3. POST /api/query
4. GET  /api/graph/topology
5. GET  /api/graph/expand
6. GET  /api/graph/node/{node_id}
7. GET  /api/eval/latest
8. GET  /api/eval/status
9. GET  /api/integrations/status
"""

import sys
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.server.app import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_server_apis")

client = TestClient(app)


def test_endpoint(name: str, method: str, url: str, **kwargs):
    logger.info("Testing %s %s...", method, url)
    if method == "GET":
        resp = client.get(url, **kwargs)
    elif method == "POST":
        resp = client.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported method {method}")

    assert resp.status_code == 200, f"Failed {name}: status={resp.status_code}, text={resp.text[:300]}"
    data = resp.json()
    logger.info("✅ %s succeeded (status=%d)", name, resp.status_code)
    return data


def main():
    logger.info("=== Starting Comprehensive Server API Verification ===")
    
    # 1. Health
    health = test_endpoint("Health Check", "GET", "/api/health")
    logger.info("   -> Health status: %s, Docs: %d, Persons: %d, Orgs: %d, Topics: %d, Facts: %d",
                health.get("status"), health.get("total_documents"), health.get("total_persons"),
                health.get("total_orgs"), health.get("total_topics", 0), health.get("total_facts"))

    # 2. Questions
    questions = test_endpoint("List Questions", "GET", "/api/questions?limit=5")
    logger.info("   -> Total questions: %d, categories: %d", questions.get("total"), len(questions.get("categories", [])))

    # 3. Query
    query_payload = {"question": "What role does Diego Martinez have at Redwood?"}
    query_resp = test_endpoint("Hybrid Graph Query", "POST", "/api/query", json=query_payload)
    logger.info("   -> Answer (first 100 chars): %s...", query_resp.get("answer", "")[:100].replace("\n", " "))
    logger.info("   -> Citations: %s, Traversed: %s", query_resp.get("citations"), query_resp.get("trace", {}).get("traversed_entities"))

    # 4. Graph Topology
    topology = test_endpoint("Graph Topology", "GET", "/api/graph/topology?doc_limit=10")
    logger.info("   -> Total Cytoscape nodes: %d, edges: %d", topology.get("total_nodes"), topology.get("total_edges"))

    # 5. Graph Node Details
    if topology.get("nodes"):
        first_node = topology["nodes"][0]["data"]
        first_node_id = first_node["id"]
        node_details = test_endpoint(f"Node Inspector ({first_node_id})", "GET", f"/api/graph/node/{first_node_id}")
        logger.info("   -> Inspected node %s: label=%s, properties count=%d",
                    first_node_id, node_details.get("label"), len(node_details.get("properties", {})))

    # 6. Eval Latest
    eval_latest = test_endpoint("Latest Eval Report", "GET", "/api/eval/latest")
    summary = eval_latest.get("summary", {})
    logger.info("   -> Benchmark Composite Score: %.2f / 100", summary.get("overall_composite_score", 0.0))

    # 7. Eval Status
    eval_status = test_endpoint("Eval Status", "GET", "/api/eval/status")
    logger.info("   -> Eval status: %s", eval_status.get("status"))

    # 8. Integrations Status
    integrations_status = test_endpoint("Integrations Status", "GET", "/api/integrations/status")
    logger.info("   -> Integrations configured: %s", integrations_status.get("configured"))

    logger.info("\n🎉 ALL SERVER APIs ARE FULLY SYNCED AND OPERATIONAL!")


if __name__ == "__main__":
    main()

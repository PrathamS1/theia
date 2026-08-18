"""
src/company_brain/server/app.py — Main FastAPI Application Entrypoint.

Starts REST API server on http://127.0.0.1:8000 for:
1. /api/health       - HydraDB & Vector Store status
2. /api/graph/...    - Graph topology and node inspector
3. /api/questions    - Benchmark questions browser
4. /api/query        - Live query engine with visual trace
5. /api/eval/...     - Benchmark evaluation trigger & dashboard
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from company_brain.server.routes.health import router as health_router
from company_brain.server.routes.graph import router as graph_router
from company_brain.server.routes.query import router as query_router
from company_brain.server.routes.eval import router as eval_router

app = FastAPI(
    title="Theia: Enterprise Company Brain on HydraDB",
    description="Graph-Augmented Enterprise Intelligence Platform with Multi-Hop Reasoning and Temporal Conflict Supersession.",
    version="1.0.0",
)

# Enable CORS for local development and frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health_router)
app.include_router(graph_router)
app.include_router(query_router)
app.include_router(eval_router)

# Mount Static Files directory if it exists
static_dir = Path(__file__).resolve().parent / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to /static/index.html or OpenAPI docs."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return RedirectResponse(url="/static/index.html")
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print("  🚀 STARTING THEIA FASTAPI SERVER ON http://127.0.0.1:8000")
    print("  📖 API Documentation: http://127.0.0.1:8000/docs")
    print("=" * 70 + "\n")
    uvicorn.run("company_brain.server.app:app", host="0.0.0.0", port=8000, reload=True)

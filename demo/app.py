"""
demo/app.py — Streamlit Interactive Demo Interface for Company Brain.

Features:
- Ask natural language questions against Redwood Inference knowledge graph
- View answer + citations
- View graph paths traversed in HydraDB
- View conflict layer supersedes & trust score breakdown
- View abstention alerts
"""

import sys
from pathlib import Path
import streamlit as st

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient
from company_brain.query.engine import answer_question

st.set_page_config(
    page_title="Company Brain — Hack Hydra 2026",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Company Brain")
st.caption("Conflict-Aware, Provenance-Tracking Enterprise Graph on HydraDB · Hack Hydra 2026")

# Sidebar info
with st.sidebar:
    st.header("⚙️ System Status")
    try:
        with GraphClient() as client:
            connected = client.ping()
            if connected:
                st.success("HydraDB Connected (bolt://127.0.0.1:7687)")
                
                try:
                    st.subheader("📊 Graph Statistics")
                    docs = client.run("MATCH (n:Document) RETURN count(*)")[0]["count(*)"]
                    facts = client.run("MATCH (n:Fact) RETURN count(*)")[0]["count(*)"]
                    persons = client.run("MATCH (n:Person) RETURN count(*)")[0]["count(*)"]
                    resolved = client.run("MATCH ()-[r:SAME_AS]->() RETURN count(*)")[0]["count(*)"]
                    
                    st.markdown(f"- **Documents:** {docs:,}")
                    st.markdown(f"- **Facts:** {facts:,}")
                    st.markdown(f"- **Persons:** {persons:,}")
                    st.markdown(f"- **Resolved Links:** {resolved:,}")
                except Exception as e:
                    st.warning("Could not load stats")
            else:
                st.error("HydraDB Disconnected")
    except Exception as e:
        st.error(f"Connection Error: {e}")

    st.markdown("---")
    st.subheader("📚 Quick Sample Questions")
    samples = [
        "What are the default size limits for file uploads on OpenAI endpoints?",
        "What failover sequence did MedThink specify for EU region outages?",
        "What is the company policy for contractor access expiration?",
    ]
    for sample in samples:
        if st.button(sample, use_container_width=True):
            st.session_state["user_query"] = sample

# Query Input
st.markdown("---")
use_llm = st.checkbox("Enable LLM Synthesis (Turn off if hitting API rate limits)", value=False)

user_query = st.text_input(
    "Ask a question about Redwood Inference internal documents:",
    value=st.session_state.get("user_query", ""),
    placeholder="e.g. What are the default size limits for multipart file uploads?",
)

if user_query:
    st.markdown("### 🔍 Answer & Graph Traversal")
    with st.spinner("Traversing HydraDB graph & generating answer..."):
        try:
            with GraphClient() as client:
                res = answer_question(user_query, client, use_llm=use_llm)
            
            if res.abstained:
                st.warning("⚠️ **Abstention Triggered** (Not in Data)")
                st.info(res.answer)
            else:
                st.success("✅ **Answer Generated**")
                st.markdown(f"**Answer:** {res.answer}")

                if res.citations:
                    st.markdown("#### 📄 Document Citations")
                    for cit in res.citations:
                        st.code(f"doc_id: {cit}", language="text")

        except Exception as e:
            st.error(f"Error executing query: {e}")

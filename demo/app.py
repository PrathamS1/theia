"""
demo/app.py — Streamlit Interactive Demo Interface for Company Brain.
"""

import sys
from pathlib import Path
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_brain.graph.client import GraphClient
from company_brain.query.engine import answer_question

st.set_page_config(
    page_title="THEIA — Hack Hydra 2026",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced Custom CSS for Premium Dashboard Look
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Main Background & Text */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* Chat Input Bar */
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    .stChatInputContainer textarea {
        background-color: #1f2937;
        color: white;
        border: 1px solid #374151;
        border-radius: 12px;
    }
    .stChatInputContainer textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 1px #3b82f6;
    }
    
    /* Suggested Question Buttons (Pills) */
    .stButton button {
        background-color: #1f2937;
        color: #9ca3af;
        border-radius: 20px;
        border: 1px solid #374151;
        padding: 4px 12px;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #374151;
        color: white;
        border-color: #4b5563;
    }
    
    /* Chat Messages */
    .stChatMessage {
        background-color: transparent;
        padding: 1rem 0;
    }
    [data-testid="chatAvatarIcon-user"] {
        background-color: #3b82f6;
    }
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #10b981;
    }
    
    /* Source Cards */
    .source-card {
        background-color: #1f2937;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #374151;
        margin-bottom: 10px;
        font-size: 0.9rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .source-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-color: #4b5563;
    }
    .source-badge {
        display: inline-block;
        background-color: #374151;
        color: #d1d5db;
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.7rem;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        color: #3b82f6 !important;
        border-bottom: 2px solid #3b82f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Logo & Header
THEIA_SVG = """
<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 12px;">
  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
  <circle cx="12" cy="12" r="3"></circle>
</svg>
"""
st.sidebar.markdown(f"<h2 style='display: flex; align-items: center; margin-top: 0;'>{THEIA_SVG} THEIA</h2>", unsafe_allow_html=True)
st.sidebar.caption("Enterprise Graph Intelligence")
st.sidebar.markdown("---")

# Sidebar - Settings & Stats
with st.sidebar:
    st.markdown("### Settings")
    use_llm = st.toggle("Enable LLM Synthesis", value=False, help="Uses AI to write fluent answers. Turn off if hitting rate limits.")
    
    st.markdown("### System Status")
    try:
        with GraphClient() as client:
            connected = client.ping()
            if connected:
                st.success("● Connected to HydraDB")
                
                try:
                    docs = client.run_read("MATCH (n:Document) RETURN count(*)")[0]["count(*)"]
                    facts = client.run_read("MATCH (n:Fact) RETURN count(*)")[0]["count(*)"]
                    persons = client.run_read("MATCH (n:Person) RETURN count(*)")[0]["count(*)"]
                    
                    st.markdown(f"""
                    <div style='background-color: #1f2937; padding: 15px; border-radius: 8px; border: 1px solid #374151;'>
                        <div style='font-size: 0.8rem; color: #9ca3af;'>Documents</div>
                        <div style='font-size: 1.5rem; font-weight: 600; margin-bottom: 10px;'>{docs:,}</div>
                        <div style='font-size: 0.8rem; color: #9ca3af;'>Extracted Facts</div>
                        <div style='font-size: 1.5rem; font-weight: 600; margin-bottom: 10px;'>{facts:,}</div>
                        <div style='font-size: 0.8rem; color: #9ca3af;'>Entities Resolved</div>
                        <div style='font-size: 1.5rem; font-weight: 600;'>{persons:,}</div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    pass
            else:
                st.error("○ Disconnected")
    except Exception:
        pass

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_citations" not in st.session_state:
    st.session_state.last_citations = []
if "suggested_query" not in st.session_state:
    st.session_state.suggested_query = None

# Main Content
tab1, tab2 = st.tabs(["Ask AI", "Graph Explorer"])

with tab1:
    st.markdown("<h3 style='margin-bottom: 2rem;'>Ask a question about company knowledge</h3>", unsafe_allow_html=True)
    
    # Suggested Questions Row
    if not st.session_state.messages:
        st.markdown("<p style='color: #9ca3af; font-size: 0.9rem;'>Suggested questions</p>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("What are the default size limits for file uploads on OpenAI endpoints?", use_container_width=True):
                st.session_state.suggested_query = "What are the default size limits for file uploads on OpenAI endpoints?"
        with col2:
            if st.button("What failover sequence did MedThink specify for EU region outages?", use_container_width=True):
                st.session_state.suggested_query = "What failover sequence did MedThink specify for EU region outages?"
        with col3:
            if st.button("What is the company policy for contractor access expiration?", use_container_width=True):
                st.session_state.suggested_query = "What is the company policy for contractor access expiration?"

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                st.markdown("##### Sources")
                cols = st.columns(min(len(msg["citations"]), 3))
                for i, cit in enumerate(msg["citations"]):
                    with cols[i % 3]:
                        st.markdown(f"""
                        <div class="source-card">
                            <div class="source-badge">Source {i+1}</div>
                            <div style="color: #9ca3af; font-family: monospace; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {cit}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # Chat Input
    prompt = st.chat_input("Ask a question...")
    
    # Handle either suggested query or manual input
    query_to_run = prompt or st.session_state.suggested_query
    
    if query_to_run:
        # Clear suggested query once used
        st.session_state.suggested_query = None
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query_to_run})
        with st.chat_message("user"):
            st.markdown(query_to_run)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching HydraDB..."):
                try:
                    with GraphClient() as client:
                        res = answer_question(query_to_run, client, force_heuristic=not use_llm)
                    
                    st.session_state.last_citations = res.citations
                    
                    if res.abstained:
                        response_content = "⚠️ **No authoritative answer found in the knowledge base.**\n\n" + res.answer
                    else:
                        response_content = res.answer
                        
                    st.markdown(response_content)
                    
                    if res.citations:
                        st.markdown("##### Sources")
                        cols = st.columns(min(len(res.citations), 3))
                        for i, cit in enumerate(res.citations):
                            with cols[i % 3]:
                                st.markdown(f"""
                                <div class="source-card">
                                    <div class="source-badge">Source {i+1}</div>
                                    <div style="color: #9ca3af; font-family: monospace; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        {cit}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_content,
                        "citations": res.citations
                    })
                    
                except Exception as e:
                    st.error(f"Failed to query knowledge graph: {e}")

with tab2:
    citations = st.session_state.last_citations
    
    if not citations:
        st.info("👈 Ask a question in the 'Ask AI' tab to visualize its source graph.")
    else:
        st.markdown("### Source Dependency Graph")
        nodes = []
        edges = []
        added_nodes = set()
        
        with st.spinner("Rendering graph..."):
            try:
                with GraphClient() as client:
                    for doc_id in citations:
                        if doc_id not in added_nodes:
                            nodes.append(Node(id=doc_id, label="Document", title=doc_id, color="#3b82f6", shape="hexagon", size=25))
                            added_nodes.add(doc_id)
                        
                        cypher = """
                        MATCH (d:Document {doc_id: $did})-[:HAS_FACT]->(f:Fact)
                        RETURN f.id AS fact_id, f.subject AS subject, f.attribute AS attr, f.value AS val
                        LIMIT 15
                        """
                        records = client.run_read(cypher, {"did": doc_id})
                        
                        for rec in records:
                            fact_id = str(rec.get("fact_id"))
                            if not fact_id or fact_id == "None":
                                continue
                                
                            if fact_id not in added_nodes:
                                subj = rec.get('subject', 'Fact')
                                attr = rec.get('attr', '')
                                label = f"{subj} - {attr}"[:25] + "..."
                                nodes.append(Node(id=fact_id, label=label, title=rec.get('val', ''), color="#8b5cf6", size=15))
                                added_nodes.add(fact_id)
                                
                            edges.append(Edge(source=doc_id, target=fact_id, label="HAS_FACT", color="#4b5563"))
                
                config = Config(
                    width="100%", 
                    height=700, 
                    directed=True,
                    physics=True, 
                    hierarchical=False,
                    nodeHighlightBehavior=True, 
                    highlightColor="#f3f4f6",
                    collapsible=False,
                    nodeSpacing=150,
                    edges={"smooth": {"type": "continuous"}},
                )
                
                agraph(nodes=nodes, edges=edges, config=config)
                
            except Exception as e:
                st.error(f"Failed to build graph: {e}")

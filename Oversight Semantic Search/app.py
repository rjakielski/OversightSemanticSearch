from __future__ import annotations

import streamlit as st

from oversight_semantic_search.index import SemanticSearchIndex

st.set_page_config(
    page_title="Oversight Semantic Search",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp {
        background:
          radial-gradient(circle at top right, rgba(191, 219, 254, 0.45), transparent 28%),
          radial-gradient(circle at bottom left, rgba(187, 247, 208, 0.35), transparent 24%),
          linear-gradient(135deg, #f8fafc, #eff6ff 45%, #ecfeff 100%);
      }
      .block-container {
        max-width: 1180px;
        padding-top: 2.25rem;
        padding-bottom: 2rem;
      }
      h1, h2, h3 {
        font-family: Georgia, "Times New Roman", serif;
        color: #0f172a;
      }
      .hero, .card {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 22px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
      }
      .hero {
        padding: 1.45rem 1.6rem;
        margin-bottom: 1rem;
      }
      .card {
        padding: 1rem 1.1rem;
        margin-bottom: 0.85rem;
      }
      .score {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        background: rgba(14, 116, 144, 0.12);
        color: #155e75;
        font-weight: 700;
        margin-bottom: 0.7rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>Oversight Semantic Search</h1>
      <p style="margin-bottom:0;color:#475569;font-size:1.02rem;">
        Search the OIG scrape corpus directly, or test the same retrieval logic that can be reused from the
        project proposal app to surface the most similar reports for a submitted project.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

index = SemanticSearchIndex()
with st.spinner("Preparing semantic index..."):
    index.ensure_ready()

tab_query, tab_project = st.tabs(["Standalone query", "Project similarity"])

with tab_query:
    query_text = st.text_area("Query", height=180, placeholder="Describe a topic, risk area, or oversight question")
    top_k = st.slider("Results", min_value=3, max_value=20, value=10)
    if st.button("Search reports", use_container_width=True):
        results = index.search(query_text, top_k=top_k)
        if not results:
            st.warning("No matches found. Try adding more detail or domain-specific language.")
        for result in results:
            st.markdown(
                f"""
                <div class="card">
                  <div class="score">Similarity {result["score"]:.3f}</div>
                  <h3>{result["title"]}</h3>
                  <p style="margin:0.35rem 0;color:#334155;">
                    <strong>Report ID:</strong> {result["canonical_id"]}<br>
                    <strong>Published:</strong> {result.get("publication_date") or "Unknown"}<br>
                    <strong>Agency:</strong> {result.get("agency") or "Unknown"}<br>
                    <strong>Type:</strong> {result.get("report_type") or "Unknown"}
                  </p>
                  <p style="color:#475569;">{(result.get("summary") or "No summary available.")[:450]}</p>
                  <p style="margin:0;">
                    <a href="{result["detail_url"]}" target="_blank">Open detail page</a>
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

with tab_project:
    with st.form("project_similarity_form"):
        title = st.text_input("Project title")
        objective = st.text_area("Project objective", height=180)
        submitted = st.form_submit_button("Find top 10 similar reports", use_container_width=True)

    if submitted:
        results = index.search_project(title, objective, top_k=10)
        if not results:
            st.warning("No similar reports found for that title and objective.")
        for rank, result in enumerate(results, start=1):
            st.markdown(
                f"""
                <div class="card">
                  <div class="score">#{rank} | Similarity {result["score"]:.3f}</div>
                  <h3>{result["title"]}</h3>
                  <p style="margin:0.35rem 0;color:#334155;">
                    <strong>Published:</strong> {result.get("publication_date") or "Unknown"}<br>
                    <strong>Report type:</strong> {result.get("report_type") or "Unknown"}
                  </p>
                  <p style="color:#475569;">{(result.get("summary") or "No summary available.")[:450]}</p>
                  <p style="margin:0;">
                    <a href="{result["detail_url"]}" target="_blank">Open detail page</a>
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

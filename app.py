import streamlit as st
import os
from mcp_handler import run_mcp_query
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="YOU-AI", layout="wide", page_icon="🤖")

# --- Premium CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 2rem; }

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ===== Animated background gradient ===== */
    .hero-section {
        position: relative;
        text-align: center;
        padding: 3rem 1rem 2rem 1rem;
        overflow: hidden;
    }
    .hero-section::before {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(ellipse 80% 60% at 50% -10%, rgba(124, 58, 237, 0.25), transparent),
                    radial-gradient(ellipse 60% 50% at 80% 50%, rgba(59, 130, 246, 0.1), transparent),
                    radial-gradient(ellipse 60% 50% at 20% 80%, rgba(236, 72, 153, 0.08), transparent);
        pointer-events: none;
        z-index: 0;
    }

    /* Title styling */
    .brand-title {
        font-size: 3.2rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #7C3AED 0%, #3B82F6 40%, #06B6D4 70%, #7C3AED 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 6s ease infinite;
        margin-bottom: 0.2rem;
        position: relative;
        z-index: 1;
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .brand-subtitle {
        font-size: 1.05rem;
        font-weight: 400;
        color: #94A3B8;
        margin-bottom: 2rem;
        position: relative;
        z-index: 1;
    }

    /* ===== Glass search card ===== */
    .search-card {
        background: rgba(18, 18, 26, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        max-width: 800px;
        margin: 0 auto 2rem auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                    0 0 0 1px rgba(124, 58, 237, 0.06);
        position: relative;
        z-index: 1;
    }

    /* Input styling */
    div.stTextInput > div > div > input {
        background-color: rgba(15, 15, 25, 0.8) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(124, 58, 237, 0.2) !important;
        border-radius: 14px !important;
        padding: 14px 20px !important;
        font-size: 0.95rem !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.3s ease !important;
    }
    div.stTextInput > div > div > input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15) !important;
    }
    div.stTextInput > div > div > input::placeholder {
        color: #64748B !important;
    }

    /* Button styling */
    div.stButton > button, div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 14px 28px !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        letter-spacing: 0.01em !important;
    }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%) !important;
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button:active, div.stFormSubmitButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ===== Feature pills ===== */
    .feature-pills {
        display: flex;
        justify-content: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 1.5rem;
        position: relative;
        z-index: 1;
    }
    .pill {
        background: rgba(124, 58, 237, 0.08);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 999px;
        padding: 8px 18px;
        font-size: 0.82rem;
        color: #A78BFA;
        font-weight: 500;
        letter-spacing: 0.01em;
        transition: all 0.3s ease;
        cursor: default;
    }
    .pill:hover {
        background: rgba(124, 58, 237, 0.15);
        border-color: rgba(124, 58, 237, 0.3);
        transform: translateY(-2px);
    }

    /* ===== Result container ===== */
    .result-container {
        background: rgba(18, 18, 26, 0.6);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(124, 58, 237, 0.12);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        max-width: 800px;
        margin: 1rem auto;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
        line-height: 1.7;
        color: #CBD5E1;
        font-size: 0.95rem;
        animation: fadeInUp 0.5s ease;
    }
    .result-container h1, .result-container h2, .result-container h3 {
        color: #E2E8F0;
    }
    .result-container strong {
        color: #A78BFA;
    }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ===== Status cards (stats row) ===== */
    .stats-container {
        display: flex;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
        margin: 2rem auto 0 auto;
        max-width: 800px;
        position: relative;
        z-index: 1;
    }
    .stat-card {
        background: rgba(18, 18, 26, 0.5);
        border: 1px solid rgba(124, 58, 237, 0.1);
        border-radius: 16px;
        padding: 1.2rem 2rem;
        text-align: center;
        flex: 1;
        min-width: 160px;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        border-color: rgba(124, 58, 237, 0.25);
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .stat-icon {
        font-size: 1.6rem;
        margin-bottom: 0.4rem;
    }
    .stat-label {
        font-size: 0.78rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }
    .stat-value {
        font-size: 1rem;
        color: #E2E8F0;
        font-weight: 600;
        margin-top: 0.2rem;
    }

    /* ===== Empty state ===== */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        max-width: 500px;
        margin: 0 auto;
        animation: fadeInUp 0.6s ease;
    }
    .empty-state .icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.6;
    }
    .empty-state h3 {
        color: #64748B;
        font-weight: 500;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .empty-state p {
        color: #475569;
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* ===== Divider ===== */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(124, 58, 237, 0.2), transparent);
        margin: 1.5rem auto;
        max-width: 600px;
    }

    /* ===== Spinner ===== */
    .stSpinner > div {
        border-top-color: #7C3AED !important;
    }

    /* Fix Streamlit form submit button alignment */
    div.stFormSubmitButton > button {
        margin-top: 0px !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0A0A0F; }
    ::-webkit-scrollbar-thumb { background: #2D2D3F; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #7C3AED; }

</style>
""", unsafe_allow_html=True)

# ─── Hero Section ───
st.markdown("""
<div class="hero-section">
    <div class="brand-title">YOU-AI</div>
    <div class="brand-subtitle">Your intelligent YouTube assistant — search, summarize & analyze videos with AI</div>
</div>
""", unsafe_allow_html=True)

# ─── Search Card ───
st.markdown('<div class="search-card">', unsafe_allow_html=True)

with st.form("search_form", clear_on_submit=False):
    search_query = st.text_input(
        "Ask anything",
        label_visibility="collapsed",
        placeholder="✨ Ask anything — e.g. 'Summarize the latest MKBHD video'"
    )
    
    col_url, col_btn = st.columns([4, 1])
    with col_url:
        video_url = st.text_input(
            "Target URL",
            label_visibility="collapsed",
            placeholder="🔗 Paste a YouTube URL (optional)"
        )
    with col_btn:
        submitted = st.form_submit_button("Search →")

st.markdown('</div>', unsafe_allow_html=True)

# ─── Feature Pills ───
st.markdown("""
<div class="feature-pills">
    <div class="pill">🎯 Video Summaries</div>
    <div class="pill">📝 Transcript Analysis</div>
    <div class="pill">🔍 Smart Search</div>
    <div class="pill">💡 Key Insights</div>
    <div class="pill">⚡ Powered by LLaMA 3.3</div>
</div>
""", unsafe_allow_html=True)

# ─── Divider ───
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ─── Main Content Area ───
if submitted:
    if not os.environ.get("NVIDIA_API_KEY"):
        st.error("🔑 Missing `NVIDIA_API_KEY` in your `.env` file. Please add it to connect to the LLM.")
    elif not search_query and not video_url:
        st.warning("Please enter a query or paste a YouTube URL to get started.")
    else:
        with st.spinner("🧠 YOU-AI is thinking..."):
            final_prompt = ""
            if video_url and search_query:
                final_prompt = f"Target URL: {video_url}\nRequest: {search_query}"
            elif video_url:
                final_prompt = f"Target URL: {video_url}\nPlease provide the 5 main points of this video."
            else:
                final_prompt = search_query

            try:
                result = run_mcp_query(final_prompt)
                st.markdown(f'<div class="result-container">{result}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
else:
    # ─── Empty State ───
    st.markdown("""
    <div class="empty-state">
        <div class="icon">🎬</div>
        <h3>Ready when you are</h3>
        <p>Search for a topic or paste a YouTube link above.<br>
        YOU-AI will fetch, analyze and summarize the content for you.</p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Stats Row ───
    st.markdown("""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-icon">🔗</div>
            <div class="stat-label">Powered by</div>
            <div class="stat-value">MCP Protocol</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">🧠</div>
            <div class="stat-label">Model</div>
            <div class="stat-value">LLaMA 3.3 70B</div>
        </div>
        <div class="stat-card">
            <div class="stat-icon">⚡</div>
            <div class="stat-label">Provider</div>
            <div class="stat-value">NVIDIA NIM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

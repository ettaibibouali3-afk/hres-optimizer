import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import google.generativeai as genai

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="HRES Optimizer - AI-Powered Off-Grid Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# INITIALIZE GEMINI AI
# ============================================================
@st.cache_resource
def get_gemini_model():
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")

# ============================================================
# PREMIUM CSS STYLING
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4 {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio > div > label > div > p,
    section[data-testid="stSidebar"] .stCheckbox label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stTextInput label {
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    
    section[data-testid="stSidebar"] .stSlider > div > div > div > div {
        color: #ffffff !important;
    }
    
    .hero-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0c4a6e 100%);
        padding: 2.5rem 2rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        box-shadow: 0 25px 50px rgba(0,0,0,0.4);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8 0%, #22d3ee 50%, #34d399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.8rem;
        position: relative;
        z-index: 1;
        line-height: 1.3;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: #cbd5e1;
        text-align: center;
        font-weight: 400;
        position: relative;
        z-index: 1;
        margin-bottom: 1rem;
    }
    
    .hero-badge {
        display: inline-block;
        background: linear-gradient(135deg, #0ea5e9, #0284c7);
        color: white;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.2rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .hero-badge.ai {
        background: linear-gradient(135deg, #8b5cf6, #7c3aed);
    }
    
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
        text-align: center;
    }
    
    .metric-icon {
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.2rem;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .result-card {
        background: linear-gradient(145deg, #0f172a, #1e293b);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        border: 1px solid rgba(56, 189, 248, 0.2);
        margin-bottom: 1rem;
    }
    
    .result-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #38bdf8;
    }
    
    .sizing-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .sizing-card.pv { border-top: 4px solid #f59e0b; }
    .sizing-card.wind { border-top: 4px solid #3b82f6; }
    .sizing-card.battery { border-top: 4px solid #10b981; }
    
    .sizing-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .sizing-value { font-size: 2rem; font-weight: 800; color: #ffffff; }
    .sizing-unit { font-size: 1rem; color: #94a3b8; }
    .sizing-label { font-size: 0.85rem; color: #64748b; margin-top: 0.5rem; text-transform: uppercase; }
    
    .econ-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
    }
    
    .econ-card.capex { background: linear-gradient(145deg, #1e3a5f, #0f2744); border: 1px solid rgba(59, 130, 246, 0.3); }
    .econ-card.lcoe { background: linear-gradient(145deg, #14532d, #166534); border: 1px solid rgba(34, 197, 94, 0.3); }
    .econ-card.reliability { background: linear-gradient(145deg, #4c1d95, #5b21b6); border: 1px solid rgba(167, 139, 250, 0.3); }
    
    .econ-value { font-size: 1.6rem; font-weight: 700; color: #ffffff; }
    .econ-label { font-size: 0.85rem; color: #cbd5e1; margin-top: 0.5rem; }
    
    .site-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.2rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
        text-align: center;
        margin-bottom: 0.8rem;
    }
    
    .site-name { font-size: 1.1rem; font-weight: 600; color: #ffffff; }
    .site-climate { font-size: 0.85rem; color: #94a3b8; }
    
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 12px;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #94a3b8 !important;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
        color: white !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    
    .ai-card {
        background: linear-gradient(145deg, #4c1d95, #5b21b6);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(167, 139, 250, 0.3);
        margin-bottom: 1rem;
    }
    
    .ai-title { color: #e9d5ff; font-size: 1.2rem; font-weight: 700; margin-bottom: 0.5rem; }
    .ai-content { color: #f3e8ff; line-height: 1.6; }
    
    .welcome-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 24px;
        padding: 3rem;
        text-align: center;
    }
    
    .welcome-icon { font-size: 5rem; margin-bottom: 1.5rem; }
    .welcome-title { font-size: 1.8rem; font-weight: 700; color: #ffffff; margin-bottom: 1rem; }
    .welcome-text { color: #cbd5e1; font-size: 1.1rem; line-height: 1.8; max-width: 600px; margin: 0 auto; }
    
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin: 2.5rem 0;
    }
    
    .feature-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .feature-icon { font-size: 2.5rem; margin-bottom: 0.8rem; }
    .feature-title { font-size: 1rem; font-weight: 700; color: #ffffff; }
    .feature-desc { font-size: 0.85rem; color: #94a3b8; margin-top: 0.3rem; }
    
    .footer {
        background: linear-gradient(145deg, #0f172a, #1e293b);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 3rem;
        text-align: center;
    }
    
    .footer-text { color: #94a3b8; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HERO HEADER
# ============================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">Off-Grid Hybrid PV-Wind-Battery Optimizer</div>
    <div class="hero-subtitle">AI-Powered Intelligent System Sizing for Any Location Worldwide</div>
    <div style="text-align: center;">
        <span class="hero-badge">Research Tool</span>
        <span class="hero-badge">Worldwide</span>
        <span class="hero-badge">PVGIS Data</span>
        <span class="hero-badge ai">AI-Powered (Free)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# WORLDWIDE SITES DATA
# ============================================================
PRESET_SITES = {
    "Ouarzazate, Morocco": {"lat": 30.92, "lon": -6.90, "climate": "Desert", "color": "#f59e0b"},
    "Dakhla, Morocco": {"lat": 23.72, "lon": -15.93, "climate": "Coastal", "color": "#3b82f6"},
    "Tangier, Morocco": {"lat": 35.78, "lon": -5.81, "climate": "Mediterranean", "color": "#10b981"},
    "Marrakech, Morocco": {"lat": 31.63, "lon": -8.01, "climate": "Semi-arid", "color": "#ec4899"},
    "Cairo, Egypt": {"lat": 30.04, "lon": 31.24, "climate": "Desert", "color": "#eab308"},
    "Nairobi, Kenya": {"lat": -1.29, "lon": 36.82, "climate": "Tropical", "color": "#22c55e"},
    "Cape Town, South Africa": {"lat": -33.93, "lon": 18.42, "climate": "Mediterranean", "color": "#06b6d4"},
    "Madrid, Spain": {"lat": 40.42, "lon": -3.70, "climate": "Mediterranean", "color": "#ef4444"},
    "Lisbon, Portugal": {"lat": 38.72, "lon": -9.14, "climate": "Mediterranean", "color": "#22c55e"},
    "Rome, Italy": {"lat": 41.90, "lon": 12.50, "climate": "Mediterranean", "color": "#10b981"},
    "Berlin, Germany": {"lat": 52.52, "lon": 13.40, "climate": "Temperate", "color": "#64748b"},
    "Paris, France": {"lat": 48.86, "lon": 2.35, "climate": "Temperate", "color": "#3b82f6"},
    "Athens, Greece": {"lat": 37.98, "lon": 23.73, "climate": "Mediterranean", "color": "#0ea5e9"},
    "Dubai, UAE": {"lat": 25.20, "lon": 55.27, "climate": "Desert", "color": "#f59e0b"},
    "Riyadh, Saudi Arabia": {"lat": 24.69, "lon": 46.72, "climate": "Desert", "color": "#eab308"},
    "Tel Aviv, Israel": {"lat": 32.08, "lon": 34.78, "climate": "Mediterranean", "color": "#3b82f6"},
    "New Delhi, India": {"lat": 28.61, "lon": 77.21, "climate": "Semi-arid", "color": "#f97316"},
    "Mumbai, India": {"lat": 19.08, "lon": 72.88, "climate": "Tropical", "color": "#8b5cf6"},
    "Beijing, China": {"lat": 39.90, "lon": 116.41, "climate": "Continental", "color": "#dc2626"},
    "Tokyo, Japan": {"lat": 35.68, "lon": 139.69, "climate": "Humid", "color": "#ec4899"},
    "Bangkok, Thailand": {"lat": 13.76, "lon": 100.50, "climate": "Tropical", "color": "#22c55e"},
    "Singapore": {"lat": 1.35, "lon": 103.82, "climate": "Tropical", "color": "#ef4444"},
    "Phoenix, USA": {"lat": 33.45, "lon": -112.07, "climate": "Desert", "color": "#f59e0b"},
    "Los Angeles, USA": {"lat": 34.05, "lon": -118.24, "climate": "Mediterranean", "color": "#f97316"},
    "Miami, USA": {"lat": 25.76, "lon": -80.19, "climate": "Tropical", "color": "#06b6d4"},
    "Mexico City, Mexico": {"lat": 19.43, "lon": -99.13, "climate": "Subtropical", "color": "#22c55e"},
    "Sao Paulo, Brazil": {"lat": -23.55, "lon": -46.63, "climate": "Tropical", "color": "#eab308"},
    "Santiago, Chile": {"lat": -33.45, "lon": -70.67, "climate": "Mediterranean", "color": "#dc2626"},
    "Sydney, Australia": {"lat": -33.87, "lon": 151.21, "climate": "Temperate", "color": "#0ea5e9"},
    "Perth, Australia": {"lat": -31.95, "lon": 115.86, "climate": "Mediterranean", "color": "#f59e0b"},
    "Auckland, New Zealand": {"lat": -36.85, "lon": 174.76, "climate": "Temperate", "color": "#22c55e"},
}

REGIONS = {
    "Africa": ["Ouarzazate, Morocco", "Dakhla, Morocco", "Tangier, Morocco", "Marrakech, Morocco", "Cairo, Egypt", "Nairobi, Kenya", "Cape Town, South Africa"],
    "Europe": ["Madrid, Spain", "Lisbon, Portugal", "Rome, Italy", "Berlin, Germany", "Paris, France", "Athens, Greece"],
    "Middle East": ["Dubai, UAE", "Riyadh, Saudi Arabia", "Tel Aviv, Israel"],
    "Asia": ["New Delhi, India", "Mumbai, India", "Beijing, China", "Tokyo, Japan", "Bangkok, Thailand", "Singapore"],
    "Americas": ["Phoenix, USA", "Los Angeles, USA", "Miami, USA", "Mexico City, Mexico", "Sao Paulo, Brazil", "Santiago, Chile"],
    "Oceania": ["Sydney, Australia", "Perth, Australia", "Auckland, New Zealand"],
}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## Configuration")
    
    st.markdown("### Location")
    site_option = st.radio("Select type:", ["Preset Locations", "Custom Coordinates"])
    
    if site_option == "Preset Locations":
        selected_region = st.selectbox("Select region:", list(REGIONS.keys()))
        selected_sites = st.multiselect(
            "Select site(s):",
            REGIONS[selected_region],
            default=[REGIONS[selected_region][0]]
        )
        if not selected_sites:
            selected_sites = [REGIONS[selected_region][0]]
    else:
        custom_lat = st.number_input("Latitude (-60 to 70)", value=30.0, min_value=-60.0, max_value=70.0, step=0.1)
        custom_lon = st.number_input("Longitude (-180 to 180)", value=0.0, min_value=-180.0, max_value=180.0, step=0.1)
        custom_name = st.text_input("Location name", value="Custom Location")
        selected_sites = [custom_name]
        PRESET_SITES[custom_name] = {"lat": custom_lat, "lon": custom_lon, "climate": "Custom", "color": "#64748b"}
    
    st.divider()
    
    st.markdown("### Load Profile")
    load_type = st.radio("Load type:", ["Fixed Load", "Variable Load"])
    
    if load_type == "Fixed Load":
        load_kw = st.slider("Constant load (kW)", 1, 50, 5)
    else:
        st.info("Residential pattern: 1.5-7 kW")
        load_kw = 3.6
    
    st.divider()
    
    st.markdown("### Algorithm")
    algorithm = st.selectbox("Select algorithm:", ["PSO", "GA", "GWO", "Compare All"])
    lpsp_target = st.slider("Max LPSP (%)", 1, 20, 5) / 100
    
    st.divider()
    
    st.markdown("### Costs")
    cost_pv = st.slider("PV ($/kW)", 200, 1500, 600, step=50)
    cost_wind = st.slider("Wind ($/kW)", 500, 2000, 1000, step=50)
    cost_batt = st.slider("Battery ($/kWh)", 100, 500, 250, step=25)
    
    st.divider()
    
    run_optimization = st.button("OPTIMIZE", type="primary", use_container_width=True)

# ============================================================
# CORE FUNCTIONS
# ============================================================
def create_load_profile(load_type, base_load=5):
    if load_type == "Fixed Load":
        return np.full(8760, base_load)
    else:
        hourly_pattern = {
            0: 2.0, 1: 1.5, 2: 1.5, 3: 1.5, 4: 1.5, 5: 2.0,
            6: 3.5, 7: 5.0, 8: 4.5, 9: 3.5, 10: 3.0, 11: 3.0,
            12: 4.0, 13: 4.0, 14: 3.5, 15: 3.0, 16: 3.5, 17: 5.0,
            18: 6.5, 19: 7.0, 20: 6.5, 21: 5.5, 22: 4.0, 23: 2.5
        }
        return np.array([hourly_pattern[h % 24] for h in range(8760)])

def pv_power(ghi, temp, P_rated):
    ghi = np.array(ghi).flatten()
    temp = np.array(temp).flatten()
    T_cell = temp + 25 * (ghi / 800)
    temp_factor = 1 + (-0.4 / 100) * (T_cell - 25)
    P_pv = P_rated * (ghi / 1000) * temp_factor * 0.9
    return np.clip(P_pv, 0, P_rated)

def wind_power(ws, P_rated):
    ws = np.array(ws).flatten()
    v_hub = ws * (30 / 10) ** 0.14
    A = np.pi * 100
    P = 0.5 * 1.225 * A * (v_hub ** 3) * 0.361 / 1000
    P = np.where(v_hub < 3, 0, P)
    P = np.where(v_hub > 25, 0, P)
    return np.clip(P, 0, P_rated)

def simulate(ghi, ws, temp, Ppv, Pw, Bc, load_profile):
    pv = pv_power(ghi, temp, Ppv)
    wind = wind_power(ws, Pw)
    gen = pv + wind
    n = len(ghi)
    soc = np.zeros(n)
    unmet = np.zeros(n)
    dump = np.zeros(n)
    soc[0] = 0.5
    
    for t in range(n):
        Pl = float(load_profile[t])
        net = float(gen[t]) - Pl
        if net >= 0:
            charge = min(net * 0.95, (1.0 - soc[t]) * Bc)
            soc_new = soc[t] + charge / Bc
            dump[t] = net - charge / 0.95
        else:
            need = -net / 0.95
            avail = (soc[t] - 0.2) * Bc
            if need <= avail:
                soc_new = soc[t] - need / Bc
            else:
                unmet[t] = -net - avail * 0.95
                soc_new = 0.2
        if t < n - 1:
            soc[t + 1] = soc_new
    
    Epv = np.sum(pv)
    Ew = np.sum(wind)
    Eload = np.sum(load_profile)
    Eserved = Eload - np.sum(unmet)
    lpsp = np.sum(unmet) / Eload if Eload > 0 else 0
    reliability = (1 - lpsp) * 100
    
    return {
        "pv": pv, "wind": wind, "gen": gen, "soc": soc,
        "unmet": unmet, "dump": dump, "Epv": Epv, "Ew": Ew,
        "Eload": Eload, "Eserved": Eserved, "lpsp": lpsp, "reliability": reliability
    }

def lcoe(Ppv, Pw, Bc, Eserved, cost_pv, cost_wind, cost_batt):
    capex = Ppv * cost_pv + Pw * cost_wind + Bc * cost_batt
    crf = 0.08 * 1.08**25 / (1.08**25 - 1)
    annual_cost = capex * crf + capex * 0.015
    lcoe_val = annual_cost / Eserved if Eserved > 0 else float("inf")
    return lcoe_val, capex

def objective(x, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt):
    Ppv, Pw, Bc = x
    if Ppv < 0 or Pw < 0 or Bc < 0:
        return 1e9
    sim = simulate(ghi, ws, temp, Ppv, Pw, Bc, load_profile)
    cost, _ = lcoe(Ppv, Pw, Bc, sim["Eserved"], cost_pv, cost_wind, cost_batt)
    if sim["lpsp"] > lpsp_max:
        return cost + 1e6 * (sim["lpsp"] - lpsp_max)
    return cost

def pso_optimize(ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt, progress=None):
    np.random.seed(42)
    bounds = [(5, 100), (5, 100), (50, 500)]
    n_part, n_iter = 20, 50
    parts = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_part)])
    vels = np.zeros_like(parts)
    pbest = parts.copy()
    pbest_f = np.array([objective(p, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for p in parts])
    gbest = pbest[np.argmin(pbest_f)].copy()
    gbest_f = np.min(pbest_f)
    hist = [gbest_f]
    
    for it in range(n_iter):
        for i in range(n_part):
            r1, r2 = np.random.rand(3), np.random.rand(3)
            vels[i] = 0.7 * vels[i] + 1.5 * r1 * (pbest[i] - parts[i]) + 1.5 * r2 * (gbest - parts[i])
            parts[i] = np.clip(parts[i] + vels[i], [b[0] for b in bounds], [b[1] for b in bounds])
            f = objective(parts[i], ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt)
            if f < pbest_f[i]:
                pbest[i], pbest_f[i] = parts[i].copy(), f
                if f < gbest_f:
                    gbest, gbest_f = parts[i].copy(), f
        hist.append(gbest_f)
        if progress:
            progress.progress((it + 1) / n_iter)
    
    return {"solution": gbest, "fitness": gbest_f, "history": hist, "algorithm": "PSO"}

def ga_optimize(ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt, progress=None):
    np.random.seed(42)
    bounds = [(5, 100), (5, 100), (50, 500)]
    pop_size, n_iter = 20, 50
    pop = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(pop_size)])
    fitness = np.array([objective(p, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for p in pop])
    gbest = pop[np.argmin(fitness)].copy()
    gbest_f = np.min(fitness)
    hist = [gbest_f]
    
    for it in range(n_iter):
        new_pop = []
        for _ in range(pop_size):
            i, j = np.random.randint(0, pop_size, 2)
            winner = pop[i] if fitness[i] < fitness[j] else pop[j]
            new_pop.append(winner.copy())
        new_pop = np.array(new_pop)
        
        for i in range(0, pop_size - 1, 2):
            if np.random.rand() < 0.8:
                alpha = np.random.rand(3)
                new_pop[i], new_pop[i+1] = alpha * new_pop[i] + (1-alpha) * new_pop[i+1], (1-alpha) * new_pop[i] + alpha * new_pop[i+1]
        
        for i in range(pop_size):
            if np.random.rand() < 0.1:
                j = np.random.randint(0, 3)
                new_pop[i, j] = np.random.uniform(bounds[j][0], bounds[j][1])
        
        for d in range(3):
            new_pop[:, d] = np.clip(new_pop[:, d], bounds[d][0], bounds[d][1])
        
        pop = new_pop
        fitness = np.array([objective(p, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for p in pop])
        
        if np.min(fitness) < gbest_f:
            gbest, gbest_f = pop[np.argmin(fitness)].copy(), np.min(fitness)
        hist.append(gbest_f)
        if progress:
            progress.progress((it + 1) / n_iter)
    
    return {"solution": gbest, "fitness": gbest_f, "history": hist, "algorithm": "GA"}

def gwo_optimize(ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt, progress=None):
    np.random.seed(42)
    bounds = [(5, 100), (5, 100), (50, 500)]
    n_wolves, n_iter = 20, 50
    wolves = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_wolves)])
    fitness = np.array([objective(w, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for w in wolves])
    
    sorted_idx = np.argsort(fitness)
    alpha, beta, delta = wolves[sorted_idx[0]].copy(), wolves[sorted_idx[1]].copy(), wolves[sorted_idx[2]].copy()
    alpha_f = fitness[sorted_idx[0]]
    hist = [alpha_f]
    
    for it in range(n_iter):
        a = 2 - 2 * (it / n_iter)
        for i in range(n_wolves):
            for d in range(3):
                r1, r2 = np.random.rand(), np.random.rand()
                A1, C1 = 2 * a * r1 - a, 2 * r2
                X1 = alpha[d] - A1 * abs(C1 * alpha[d] - wolves[i, d])
                
                r1, r2 = np.random.rand(), np.random.rand()
                A2, C2 = 2 * a * r1 - a, 2 * r2
                X2 = beta[d] - A2 * abs(C2 * beta[d] - wolves[i, d])
                
                r1, r2 = np.random.rand(), np.random.rand()
                A3, C3 = 2 * a * r1 - a, 2 * r2
                X3 = delta[d] - A3 * abs(C3 * delta[d] - wolves[i, d])
                
                wolves[i, d] = np.clip((X1 + X2 + X3) / 3, bounds[d][0], bounds[d][1])
        
        fitness = np.array([objective(w, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for w in wolves])
        sorted_idx = np.argsort(fitness)
        
        if fitness[sorted_idx[0]] < alpha_f:
            alpha, alpha_f = wolves[sorted_idx[0]].copy(), fitness[sorted_idx[0]]
        beta, delta = wolves[sorted_idx[1]].copy(), wolves[sorted_idx[2]].copy()
        hist.append(alpha_f)
        if progress:
            progress.progress((it + 1) / n_iter)
    
    return {"solution": alpha, "fitness": alpha_f, "history": hist, "algorithm": "GWO"}

@st.cache_data(ttl=3600)
def fetch_data(lat, lon):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {"lat": lat, "lon": lon, "outputformat": "json", "usehorizon": 1, "startyear": 2005, "endyear": 2023}
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        df = pd.DataFrame(r.json()["outputs"]["tmy_hourly"])
        df = df.rename(columns={"G(h)": "GHI", "T2m": "temp", "WS10m": "wind_speed"})
        df["wind_speed"] = df["wind_speed"].clip(lower=0)
        return df
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# ============================================================
# AI FUNCTIONS (FREE GEMINI)
# ============================================================
def get_ai_recommendations(site_name, sol, lcoe_val, capex, sim, df, cost_pv, cost_wind, cost_batt):
    try:
        model = get_gemini_model()
        
        prompt = f"""You are an expert in hybrid renewable energy systems. Analyze this system and provide 4-5 specific, actionable recommendations.

SYSTEM DETAILS:
- Location: {site_name}
- Climate: {PRESET_SITES.get(site_name, {}).get("climate", "Unknown")}

OPTIMAL SIZING:
- PV Capacity: {sol[0]:.1f} kW
- Wind Capacity: {sol[1]:.1f} kW
- Battery Storage: {sol[2]:.1f} kWh

ECONOMICS:
- CAPEX: ${capex:,.0f}
- LCOE: {lcoe_val*100:.2f} cents/kWh

PERFORMANCE:
- Reliability: {sim["reliability"]:.1f}%
- Annual Solar Energy: {sim["Epv"]/1000:.1f} MWh
- Annual Wind Energy: {sim["Ew"]/1000:.1f} MWh

RESOURCES:
- Annual GHI: {df["GHI"].sum()/1000:.0f} kWh/m2/year
- Average Wind Speed: {df["wind_speed"].mean():.1f} m/s

Provide specific recommendations for optimization, cost reduction, and reliability. Be concise."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def generate_ai_report(site_name, sol, lcoe_val, capex, sim, df):
    try:
        model = get_gemini_model()
        
        prompt = f"""Generate a professional technical report for this hybrid renewable energy system.

LOCATION: {site_name}
CLIMATE: {PRESET_SITES.get(site_name, {}).get("climate", "Unknown")}

SYSTEM:
- PV: {sol[0]:.1f} kW
- Wind: {sol[1]:.1f} kW
- Battery: {sol[2]:.1f} kWh

ECONOMICS:
- CAPEX: ${capex:,.0f}
- LCOE: {lcoe_val*100:.2f} cents/kWh

PERFORMANCE:
- Reliability: {sim["reliability"]:.1f}%
- PV Energy: {sim["Epv"]/1000:.1f} MWh/year
- Wind Energy: {sim["Ew"]/1000:.1f} MWh/year

Include: Executive Summary, System Configuration, Economic Analysis, Technical Performance, Recommendations, Conclusion.
Format in Markdown."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def ai_chat_response(user_question, context_data):
    try:
        model = get_gemini_model()
        
        prompt = f"""You are an AI assistant for a hybrid renewable energy optimization platform. Answer based on this context:

{context_data}

USER QUESTION: {user_question}

Provide a helpful, accurate answer. Use specific numbers when relevant."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================
# SESSION STATE
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "optimization_results" not in st.session_state:
    st.session_state.optimization_results = None
if "current_context" not in st.session_state:
    st.session_state.current_context = ""

# ============================================================
# MAIN APP
# ============================================================
if run_optimization:
    all_results = {}
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Results", "Analysis", "Dispatch", "AI Assistant", "Export"])
    
    with tab1:
        for site_name in selected_sites:
            site_info = PRESET_SITES[site_name]
            
            st.markdown(f'<div class="result-card"><div class="result-title">{site_name} ({site_info["climate"]})</div></div>', unsafe_allow_html=True)
            
            with st.spinner(f"Fetching data for {site_name}..."):
                df = fetch_data(site_info["lat"], site_info["lon"])
            
            if df is None:
                continue
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">☀️</div><div class="metric-value">{df["GHI"].sum()/1000:.0f}</div><div class="metric-label">kWh/m2/year</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">💨</div><div class="metric-value">{df["wind_speed"].mean():.1f}</div><div class="metric-label">m/s avg wind</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="metric-card"><div class="metric-icon">🌡️</div><div class="metric-value">{df["temp"].mean():.1f}</div><div class="metric-label">C avg temp</div></div>', unsafe_allow_html=True)
            with col4:
                lat_dir = "N" if site_info["lat"] >= 0 else "S"
                lon_dir = "E" if site_info["lon"] >= 0 else "W"
                st.markdown(f'<div class="metric-card"><div class="metric-icon">📍</div><div class="metric-value" style="font-size:1.2rem;">{abs(site_info["lat"]):.1f}{lat_dir}</div><div class="metric-label">{abs(site_info["lon"]):.1f}{lon_dir}</div></div>', unsafe_allow_html=True)
            
            st.write("")
            
            load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
            ghi, ws, temp = df["GHI"].values, df["wind_speed"].values, df["temp"].values
            
            if algorithm == "Compare All":
                st.markdown("**Running all algorithms...**")
                progress = st.progress(0)
                
                results_pso = pso_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.33)
                results_ga = ga_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.66)
                results_gwo = gwo_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(1.0)
                
                all_algo_results = [results_pso, results_ga, results_gwo]
                best_result = min(all_algo_results, key=lambda x: x["fitness"])
                
                best_marks = ["Yes" if r == best_result else "" for r in all_algo_results]
                algo_data = {
                    "Algorithm": ["PSO", "GA", "GWO"],
                    "LCOE (c/kWh)": [round(r["fitness"]*100, 2) for r in all_algo_results],
                    "PV (kW)": [round(r["solution"][0], 1) for r in all_algo_results],
                    "Wind (kW)": [round(r["solution"][1], 1) for r in all_algo_results],
                    "Battery (kWh)": [round(r["solution"][2], 1) for r in all_algo_results],
                    "Best": best_marks
                }
                st.dataframe(pd.DataFrame(algo_data), use_container_width=True, hide_index=True)
                
                result = best_result
                all_results[site_name] = {"all": all_algo_results, "best": best_result, "df": df}
            else:
                progress = st.progress(0)
                if algorithm == "PSO":
                    result = pso_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                elif algorithm == "GA":
                    result = ga_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                else:
                    result = gwo_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                
                all_results[site_name] = {"best": result, "df": df}
            
            sol = result["solution"]
            sim = simulate(ghi, ws, temp, sol[0], sol[1], sol[2], load_profile)
            lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim["Eserved"], cost_pv, cost_wind, cost_batt)
            
            st.session_state.optimization_results = {"site_name": site_name, "sol": sol, "lcoe_val": lcoe_val, "capex": capex, "sim": sim, "df": df}
            st.session_state.current_context = f"Location: {site_name}, PV: {sol[0]:.1f}kW, Wind: {sol[1]:.1f}kW, Battery: {sol[2]:.1f}kWh, CAPEX: ${capex:,.0f}, LCOE: {lcoe_val*100:.2f}c/kWh, Reliability: {sim['reliability']:.1f}%, GHI: {df['GHI'].sum()/1000:.0f}kWh/m2, Wind: {df['wind_speed'].mean():.1f}m/s"
            
            st.success(f"Optimization complete using {result['algorithm']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="sizing-card pv"><div class="sizing-icon">☀️</div><div class="sizing-value">{sol[0]:.1f} <span class="sizing-unit">kW</span></div><div class="sizing-label">PV Capacity</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="sizing-card wind"><div class="sizing-icon">💨</div><div class="sizing-value">{sol[1]:.1f} <span class="sizing-unit">kW</span></div><div class="sizing-label">Wind Capacity</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="sizing-card battery"><div class="sizing-icon">🔋</div><div class="sizing-value">{sol[2]:.1f} <span class="sizing-unit">kWh</span></div><div class="sizing-label">Battery Storage</div></div>', unsafe_allow_html=True)
            
            st.write("")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="econ-card capex"><div class="econ-value">${capex:,.0f}</div><div class="econ-label">Capital Cost</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="econ-card lcoe"><div class="econ-value">{lcoe_val*100:.2f} c/kWh</div><div class="econ-label">Levelized Cost</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="econ-card reliability"><div class="econ-value">{sim["reliability"]:.1f}%</div><div class="econ-label">Reliability</div></div>', unsafe_allow_html=True)
            
            st.write("")
            
            col1, col2 = st.columns(2)
            with col1:
                fig_pie = go.Figure(data=[go.Pie(labels=["Solar", "Wind"], values=[sim["Epv"], sim["Ew"]], hole=0.6, marker=dict(colors=["#f59e0b", "#3b82f6"]))])
                fig_pie.update_layout(title="Energy Mix", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=300)
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                fig_conv = go.Figure()
                fig_conv.add_trace(go.Scatter(y=[h*100 for h in result["history"]], mode="lines", line=dict(color="#38bdf8", width=3), fill="tozeroy", fillcolor="rgba(56,189,248,0.1)"))
                fig_conv.update_layout(title="Convergence", xaxis_title="Iteration", yaxis_title="LCOE (c/kWh)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), height=300)
                st.plotly_chart(fig_conv, use_container_width=True)
            
            st.markdown("### AI Recommendations")
            if st.button("Generate AI Recommendations", key=f"rec_{site_name}"):
                with st.spinner("AI analyzing..."):
                    recommendations = get_ai_recommendations(site_name, sol, lcoe_val, capex, sim, df, cost_pv, cost_wind, cost_batt)
                    st.markdown(f'<div class="ai-card"><div class="ai-title">AI Recommendations</div><div class="ai-content">{recommendations}</div></div>', unsafe_allow_html=True)
            
            st.divider()
    
    with tab2:
        if len(selected_sites) == 1 and all_results:
            site_name = selected_sites[0]
            if site_name in all_results:
                df = all_results[site_name]["df"]
                st.markdown("### Monthly Resource Analysis")
                df["month"] = pd.to_datetime(df["time(UTC)"], format="%Y%m%d:%H%M").dt.month
                monthly_ghi = df.groupby("month")["GHI"].sum() / 1000
                monthly_wind = df.groupby("month")["wind_speed"].mean()
                
                fig = make_subplots(rows=1, cols=2, subplot_titles=("Monthly Solar", "Monthly Wind"))
                fig.add_trace(go.Bar(x=monthly_ghi.index, y=monthly_ghi.values, marker_color="#f59e0b"), row=1, col=1)
                fig.add_trace(go.Bar(x=monthly_wind.index, y=monthly_wind.values, marker_color="#3b82f6"), row=1, col=2)
                fig.update_layout(height=350, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        if all_results:
            site_name = selected_sites[0]
            if site_name in all_results:
                df = all_results[site_name]["df"]
                result = all_results[site_name]["best"]
                sol = result["solution"]
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df["GHI"].values, df["wind_speed"].values, df["temp"].values, sol[0], sol[1], sol[2], load_profile)
                
                st.markdown("### Hourly Dispatch (Week)")
                hours = list(range(168))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hours, y=sim["pv"][:168], name="PV", fill="tozeroy", line=dict(color="#f59e0b")))
                fig.add_trace(go.Scatter(x=hours, y=sim["wind"][:168], name="Wind", fill="tozeroy", line=dict(color="#3b82f6")))
                fig.add_trace(go.Scatter(x=hours, y=load_profile[:168], name="Load", line=dict(color="#ef4444", dash="dash")))
                fig.update_layout(xaxis_title="Hour", yaxis_title="Power (kW)", height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### Battery SoC")
                fig_soc = go.Figure()
                fig_soc.add_trace(go.Scatter(x=hours, y=sim["soc"][:168]*100, fill="tozeroy", line=dict(color="#10b981")))
                fig_soc.add_hline(y=20, line_dash="dash", line_color="#ef4444")
                fig_soc.update_layout(xaxis_title="Hour", yaxis_title="SoC (%)", height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig_soc, use_container_width=True)
    
    with tab4:
        st.markdown("### AI Assistant (Free - Powered by Gemini)")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask about your results..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = ai_chat_response(prompt, st.session_state.current_context) if st.session_state.current_context else "Please run optimization first."
                    st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("**Example questions:** Why is wind at minimum? | How to reduce CAPEX? | Is this LCOE competitive?")
    
    with tab5:
        st.markdown("### Export Results")
        
        export_data = []
        for site_name in selected_sites:
            if site_name in all_results:
                result = all_results[site_name]["best"]
                df = all_results[site_name]["df"]
                sol = result["solution"]
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df["GHI"].values, df["wind_speed"].values, df["temp"].values, sol[0], sol[1], sol[2], load_profile)
                lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim["Eserved"], cost_pv, cost_wind, cost_batt)
                
                export_data.append({
                    "Site": site_name, "Lat": PRESET_SITES[site_name]["lat"], "Lon": PRESET_SITES[site_name]["lon"],
                    "Climate": PRESET_SITES[site_name]["climate"], "Algorithm": result["algorithm"],
                    "PV (kW)": round(sol[0], 2), "Wind (kW)": round(sol[1], 2), "Battery (kWh)": round(sol[2], 2),
                    "CAPEX ($)": round(capex, 2), "LCOE (c/kWh)": round(lcoe_val*100, 2), "Reliability (%)": round(sim["reliability"], 2)
                })
        
        if export_data:
            df_export = pd.DataFrame(export_data)
            st.dataframe(df_export, use_container_width=True, hide_index=True)
            st.download_button("Download CSV", df_export.to_csv(index=False), "hres_results.csv", "text/csv", use_container_width=True)
            
            st.markdown("### AI Report Generator")
            if st.button("Generate AI Report", use_container_width=True):
                if st.session_state.optimization_results:
                    with st.spinner("Generating report..."):
                        res = st.session_state.optimization_results
                        report = generate_ai_report(res["site_name"], res["sol"], res["lcoe_val"], res["capex"], res["sim"], res["df"])
                        st.markdown(report)
                        st.download_button("Download Report", report, "hres_report.md", "text/markdown", use_container_width=True)

else:
    st.markdown("""
    <div class="welcome-card">
        <div class="welcome-icon">🌍</div>
        <div class="welcome-title">AI-Powered HRES Optimizer</div>
        <div class="welcome-text">Configure parameters in sidebar and click OPTIMIZE. Now with FREE AI-powered recommendations and chat assistant!</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card"><div class="feature-icon">🌍</div><div class="feature-title">30+ Sites</div><div class="feature-desc">Worldwide</div></div>
        <div class="feature-card"><div class="feature-icon">🧠</div><div class="feature-title">3 Algorithms</div><div class="feature-desc">PSO, GA, GWO</div></div>
        <div class="feature-card"><div class="feature-icon">🤖</div><div class="feature-title">AI-Powered</div><div class="feature-desc">Free Gemini</div></div>
        <div class="feature-card"><div class="feature-icon">📊</div><div class="feature-title">Real Data</div><div class="feature-desc">PVGIS</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### Available Locations")
    map_data = [{"lat": info["lat"], "lon": info["lon"]} for info in PRESET_SITES.values()]
    st.map(pd.DataFrame(map_data), latitude="lat", longitude="lon", size=50)

st.markdown('<div class="footer"><div class="footer-text">Powered by PVGIS + Gemini AI (Free) | 2026 | Dr. Ettaibi Bouali</div></div>', unsafe_allow_html=True)

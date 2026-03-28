import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Optimization of Off-Grid Hybrid PV-Wind Systems for Enhanced Reliability and
Cost Efficiency",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# PREMIUM CSS STYLING
# ============================================================
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        position: relative;
        overflow: hidden;
    }
    
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: pulse 4s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 0.3; }
    }
    
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00d4ff 0%, #00ff88 50%, #ffaa00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
        position: relative;
        z-index: 1;
    }
    
    .hero-subtitle {
        font-size: 1.2rem;
        color: #a0aec0;
        text-align: center;
        font-weight: 400;
        position: relative;
        z-index: 1;
    }
    
    .hero-badge {
        display: inline-block;
        background: linear-gradient(135deg, #00d4ff, #0099ff);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Metric Cards */
    .metric-card {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.2rem;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Result Cards */
    .result-card {
        background: linear-gradient(145deg, #0f3460, #16213e);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(0, 212, 255, 0.2);
        margin-bottom: 1rem;
    }
    
    .result-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #00d4ff;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Sizing Cards */
    .sizing-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .sizing-card {
        background: linear-gradient(145deg, #1a1a2e, #252540);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s ease;
    }
    
    .sizing-card:hover {
        border-color: rgba(0, 212, 255, 0.3);
        transform: scale(1.02);
    }
    
    .sizing-card.pv {
        border-top: 3px solid #f59e0b;
    }
    
    .sizing-card.wind {
        border-top: 3px solid #3b82f6;
    }
    
    .sizing-card.battery {
        border-top: 3px solid #10b981;
    }
    
    .sizing-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .sizing-value {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
    }
    
    .sizing-unit {
        font-size: 1rem;
        color: #a0aec0;
        font-weight: 400;
    }
    
    .sizing-label {
        font-size: 0.9rem;
        color: #64748b;
        margin-top: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Economics Cards */
    .econ-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .econ-card {
        background: linear-gradient(145deg, #1a1a2e, #252540);
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
    }
    
    .econ-card.capex {
        background: linear-gradient(145deg, #1e3a5f, #0f2744);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    
    .econ-card.lcoe {
        background: linear-gradient(145deg, #1e4035, #0f2922);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .econ-card.reliability {
        background: linear-gradient(145deg, #3d1e5f, #2a0f44);
        border: 1px solid rgba(139, 92, 246, 0.3);
    }
    
    .econ-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
    }
    
    .econ-label {
        font-size: 0.8rem;
        color: #a0aec0;
        margin-top: 0.3rem;
    }
    
    /* Site Cards */
    .site-card {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border-radius: 16px;
        padding: 1.2rem;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .site-card:hover {
        border-color: rgba(0, 212, 255, 0.5);
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
    }
    
    .site-icon {
        font-size: 2rem;
        margin-bottom: 0.3rem;
    }
    
    .site-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff;
    }
    
    .site-climate {
        font-size: 0.85rem;
        color: #64748b;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e2e8f0;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border-radius: 12px;
        padding: 0.5rem;
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #a0aec0;
        font-weight: 600;
        padding: 0.8rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #00d4ff, #0099ff);
        color: white;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 153, 255, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0, 153, 255, 0.4);
    }
    
    /* Progress Bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #00d4ff, #00ff88);
    }
    
    /* Selectbox & Inputs */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background: #1e1e2e;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
    }
    
    /* Divider */
    hr {
        border-color: rgba(255,255,255,0.1);
    }
    
    /* Algorithm Badge */
    .algo-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .algo-badge.pso {
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
    }
    
    .algo-badge.ga {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
    }
    
    .algo-badge.gwo {
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
    }
    
    /* Footer */
    .footer {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 16px;
        padding: 1.5rem;
        margin-top: 2rem;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    .footer-text {
        color: #64748b;
        font-size: 0.85rem;
        text-align: center;
    }
    
    .footer-link {
        color: #00d4ff;
        text-decoration: none;
    }
    
    /* Welcome Card */
    .welcome-card {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border-radius: 20px;
        padding: 2rem;
        border: 1px solid rgba(255,255,255,0.05);
        text-align: center;
    }
    
    .welcome-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    
    .welcome-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    
    .welcome-text {
        color: #a0aec0;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Feature Cards */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .feature-card {
        background: linear-gradient(145deg, #1e1e2e, #252540);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        border-color: rgba(0, 212, 255, 0.3);
        transform: translateY(-3px);
    }
    
    .feature-icon {
        font-size: 1.8rem;
        margin-bottom: 0.5rem;
    }
    
    .feature-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #ffffff;
    }
    
    .feature-desc {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.3rem;
    }
    
    /* Comparison Table */
    .comparison-table {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border-radius: 16px;
        overflow: hidden;
    }
    
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-fade {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Glow Effect */
    .glow {
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HERO HEADER
# ============================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ HRES Optimizer Morocco</div>
    <div class="hero-subtitle">Intelligent Sizing of Off-Grid Hybrid PV-Wind-Battery Systems</div>
    <div style="text-align: center;">
        <span class="hero-badge">🔬 Research Tool</span>
        <span class="hero-badge">🇲🇦 Morocco Focus</span>
        <span class="hero-badge">🤖 AI-Powered</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# MOROCCO SITES DATA
# ============================================================
MOROCCO_SITES = {
    "Ouarzazate": {"lat": 30.92, "lon": -6.90, "climate": "Desert", "icon": "🏜️", "color": "#f59e0b"},
    "Dakhla": {"lat": 23.72, "lon": -15.93, "climate": "Coastal", "icon": "🌊", "color": "#3b82f6"},
    "Tangier": {"lat": 35.78, "lon": -5.81, "climate": "Mediterranean", "icon": "🌿", "color": "#10b981"},
    "Ifrane": {"lat": 33.53, "lon": -5.11, "climate": "Mountain", "icon": "🏔️", "color": "#8b5cf6"},
    "Marrakech": {"lat": 31.63, "lon": -8.01, "climate": "Semi-arid", "icon": "🌴", "color": "#ec4899"},
    "Casablanca": {"lat": 33.57, "lon": -7.59, "climate": "Coastal", "icon": "🏙️", "color": "#06b6d4"},
    "Fes": {"lat": 34.03, "lon": -5.00, "climate": "Continental", "icon": "🕌", "color": "#f97316"},
    "Agadir": {"lat": 30.43, "lon": -9.60, "climate": "Semi-arid", "icon": "☀️", "color": "#eab308"},
}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Site Selection
    st.markdown("### 📍 Location")
    site_option = st.radio("", ["Predefined Sites", "Custom Location"], label_visibility="collapsed")
    
    if site_option == "Predefined Sites":
        selected_sites = st.multiselect(
            "Select site(s):",
            list(MOROCCO_SITES.keys()),
            default=["Ouarzazate"]
        )
        if not selected_sites:
            selected_sites = ["Ouarzazate"]
    else:
        custom_lat = st.number_input("Latitude", value=31.63, min_value=20.0, max_value=36.0)
        custom_lon = st.number_input("Longitude", value=-8.01, min_value=-17.0, max_value=-1.0)
        selected_sites = ["Custom"]
        MOROCCO_SITES["Custom"] = {"lat": custom_lat, "lon": custom_lon, "climate": "Custom", "icon": "📍", "color": "#64748b"}
    
    st.divider()
    
    # Load Profile
    st.markdown("### ⚡ Load Profile")
    load_type = st.radio("", ["Fixed Load", "Variable Load"], label_visibility="collapsed")
    
    if load_type == "Fixed Load":
        load_kw = st.slider("Constant load (kW)", 1, 50, 5)
    else:
        st.info("📊 Residential: 1.5-7 kW")
        load_kw = 3.6
    
    st.divider()
    
    # Algorithm
    st.markdown("### 🧠 Algorithm")
    algorithm = st.selectbox("", ["PSO", "GA", "GWO", "Compare All"], label_visibility="collapsed")
    lpsp_target = st.slider("Max LPSP (%)", 1, 20, 5) / 100
    
    st.divider()
    
    # Costs
    st.markdown("### 💰 Costs ($/unit)")
    col1, col2 = st.columns(2)
    with col1:
        cost_pv = st.number_input("PV", value=600, step=50, label_visibility="collapsed")
        st.caption("PV $/kW")
    with col2:
        cost_wind = st.number_input("Wind", value=1000, step=50, label_visibility="collapsed")
        st.caption("Wind $/kW")
    cost_batt = st.number_input("Battery $/kWh", value=250, step=25)
    
    st.divider()
    
    # Run Button
    run_optimization = st.button("🚀 OPTIMIZE", type="primary", use_container_width=True)

# ============================================================
# FUNCTIONS
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
    
    Epv, Ew = np.sum(pv), np.sum(wind)
    Eload = np.sum(load_profile)
    Eserved = Eload - np.sum(unmet)
    lpsp = np.sum(unmet) / Eload if Eload > 0 else 0
    reliability = (1 - lpsp) * 100
    
    return {
        'pv': pv, 'wind': wind, 'gen': gen, 'soc': soc,
        'unmet': unmet, 'dump': dump,
        'Epv': Epv, 'Ew': Ew, 'Eload': Eload, 'Eserved': Eserved,
        'lpsp': lpsp, 'reliability': reliability
    }

def lcoe(Ppv, Pw, Bc, Eserved, cost_pv, cost_wind, cost_batt):
    capex = Ppv * cost_pv + Pw * cost_wind + Bc * cost_batt
    crf = 0.08 * 1.08**25 / (1.08**25 - 1)
    annual_cost = capex * crf + capex * 0.015
    lcoe_val = annual_cost / Eserved if Eserved > 0 else float('inf')
    return lcoe_val, capex

def objective(x, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt):
    Ppv, Pw, Bc = x
    if Ppv < 0 or Pw < 0 or Bc < 0:
        return 1e9
    sim = simulate(ghi, ws, temp, Ppv, Pw, Bc, load_profile)
    cost, _ = lcoe(Ppv, Pw, Bc, sim['Eserved'], cost_pv, cost_wind, cost_batt)
    if sim['lpsp'] > lpsp_max:
        return cost + 1e6 * (sim['lpsp'] - lpsp_max)
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
    
    return {'solution': gbest, 'fitness': gbest_f, 'history': hist, 'algorithm': 'PSO'}

def ga_optimize(ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt, progress=None):
    np.random.seed(42)
    bounds = [(5, 100), (5, 100), (50, 500)]
    pop_size, n_iter = 20, 50
    pop = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(pop_size)])
    fitness = np.array([objective(p, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for p in pop])
    best_idx = np.argmin(fitness)
    gbest = pop[best_idx].copy()
    gbest_f = fitness[best_idx]
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
                child1 = alpha * new_pop[i] + (1 - alpha) * new_pop[i + 1]
                child2 = (1 - alpha) * new_pop[i] + alpha * new_pop[i + 1]
                new_pop[i], new_pop[i + 1] = child1, child2
        
        for i in range(pop_size):
            if np.random.rand() < 0.1:
                j = np.random.randint(0, 3)
                new_pop[i, j] = np.random.uniform(bounds[j][0], bounds[j][1])
        
        for d in range(3):
            new_pop[:, d] = np.clip(new_pop[:, d], bounds[d][0], bounds[d][1])
        
        pop = new_pop
        fitness = np.array([objective(p, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for p in pop])
        
        if np.min(fitness) < gbest_f:
            gbest = pop[np.argmin(fitness)].copy()
            gbest_f = np.min(fitness)
        
        hist.append(gbest_f)
        if progress:
            progress.progress((it + 1) / n_iter)
    
    return {'solution': gbest, 'fitness': gbest_f, 'history': hist, 'algorithm': 'GA'}

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
                D_alpha = abs(C1 * alpha[d] - wolves[i, d])
                X1 = alpha[d] - A1 * D_alpha
                
                r1, r2 = np.random.rand(), np.random.rand()
                A2, C2 = 2 * a * r1 - a, 2 * r2
                D_beta = abs(C2 * beta[d] - wolves[i, d])
                X2 = beta[d] - A2 * D_beta
                
                r1, r2 = np.random.rand(), np.random.rand()
                A3, C3 = 2 * a * r1 - a, 2 * r2
                D_delta = abs(C3 * delta[d] - wolves[i, d])
                X3 = delta[d] - A3 * D_delta
                
                wolves[i, d] = np.clip((X1 + X2 + X3) / 3, bounds[d][0], bounds[d][1])
        
        fitness = np.array([objective(w, ghi, ws, temp, load_profile, lpsp_max, cost_pv, cost_wind, cost_batt) for w in wolves])
        sorted_idx = np.argsort(fitness)
        
        if fitness[sorted_idx[0]] < alpha_f:
            alpha, alpha_f = wolves[sorted_idx[0]].copy(), fitness[sorted_idx[0]]
        beta = wolves[sorted_idx[1]].copy()
        delta = wolves[sorted_idx[2]].copy()
        
        hist.append(alpha_f)
        if progress:
            progress.progress((it + 1) / n_iter)
    
    return {'solution': alpha, 'fitness': alpha_f, 'history': hist, 'algorithm': 'GWO'}

@st.cache_data(ttl=3600)
def fetch_data(lat, lon):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {'lat': lat, 'lon': lon, 'outputformat': 'json', 'usehorizon': 1, 'startyear': 2005, 'endyear': 2023}
    r = requests.get(url, params=params, timeout=60)
    df = pd.DataFrame(r.json()['outputs']['tmy_hourly'])
    df = df.rename(columns={'G(h)': 'GHI', 'T2m': 'temp', 'WS10m': 'wind_speed'})
    df['wind_speed'] = df['wind_speed'].clip(lower=0)
    return df

# ============================================================
# MAIN APP
# ============================================================
if run_optimization:
    all_results = {}
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Results", "📈 Analysis", "⚡ Dispatch", "📥 Export"])
    
    with tab1:
        for site_name in selected_sites:
            site_info = MOROCCO_SITES[site_name]
            
            # Site Header
            st.markdown(f"""
            <div class="result-card animate-fade">
                <div class="result-title">{site_info['icon']} {site_name} <span style="font-weight:400; font-size:1rem; color:#64748b;">({site_info['climate']})</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.spinner(f"🔄 Fetching data for {site_name}..."):
                df = fetch_data(site_info['lat'], site_info['lon'])
            
            # Resource Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">☀️</div>
                    <div class="metric-value">{df['GHI'].sum()/1000:.0f}</div>
                    <div class="metric-label">kWh/m²/year</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">💨</div>
                    <div class="metric-value">{df['wind_speed'].mean():.1f}</div>
                    <div class="metric-label">m/s avg wind</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">🌡️</div>
                    <div class="metric-value">{df['temp'].mean():.1f}°</div>
                    <div class="metric-label">avg temp</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon">📍</div>
                    <div class="metric-value" style="font-size:1.2rem;">{site_info['lat']:.2f}°N</div>
                    <div class="metric-label">{site_info['lon']:.2f}°W</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            
            # Load profile
            load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
            ghi = df['GHI'].values
            ws = df['wind_speed'].values
            temp = df['temp'].values
            
            # Run optimization
            if algorithm == "Compare All":
                st.markdown("**🧠 Running all algorithms...**")
                progress = st.progress(0)
                
                results_pso = pso_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.33)
                results_ga = ga_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.66)
                results_gwo = gwo_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(1.0)
                
                all_algo_results = [results_pso, results_ga, results_gwo]
                best_result = min(all_algo_results, key=lambda x: x['fitness'])
                
                # Comparison table
                st.markdown("**Algorithm Comparison:**")
                algo_data = {
                    'Algorithm': ['PSO', 'GA', 'GWO'],
                    'LCOE (¢/kWh)': [f"{r['fitness']*100:.2f}" for r in all_algo_results],
                    'PV (kW)': [f"{r['solution'][0]:.1f}" for r in all_algo_results],
                    'Wind (kW)': [f"{r['solution'][1]:.1f}" for r in all_algo_results],
                    'Battery (kWh)': [f"{r['solution'][2]:.1f}" for r in all_algo_results],
                    'Best': ['✅' if r == best_result else '' for r in all_algo_results]
                }
                st.dataframe(pd.DataFrame(algo_data), use_container_width=True, hide_index=True)
                
                result = best_result
                all_results[site_name] = {'all': all_algo_results, 'best': best_result, 'df': df}
            else:
                progress = st.progress(0)
                if algorithm == "PSO":
                    result = pso_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                elif algorithm == "GA":
                    result = ga_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                else:
                    result = gwo_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt, progress)
                
                all_results[site_name] = {'best': result, 'df': df}
            
            # Get results
            sol = result['solution']
            sim = simulate(ghi, ws, temp, sol[0], sol[1], sol[2], load_profile)
            lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim['Eserved'], cost_pv, cost_wind, cost_batt)
            
            st.success(f"✅ Optimization complete using **{result['algorithm']}**")
            
            # Optimal Sizing Cards
            st.markdown("### 🎯 Optimal System Sizing")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="sizing-card pv">
                    <div class="sizing-icon">☀️</div>
                    <div class="sizing-value">{sol[0]:.1f} <span class="sizing-unit">kW</span></div>
                    <div class="sizing-label">PV Capacity</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="sizing-card wind">
                    <div class="sizing-icon">💨</div>
                    <div class="sizing-value">{sol[1]:.1f} <span class="sizing-unit">kW</span></div>
                    <div class="sizing-label">Wind Capacity</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="sizing-card battery">
                    <div class="sizing-icon">🔋</div>
                    <div class="sizing-value">{sol[2]:.1f} <span class="sizing-unit">kWh</span></div>
                    <div class="sizing-label">Battery Storage</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            
            # Economics
            st.markdown("### 💰 Economic Results")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="econ-card capex">
                    <div class="econ-value">${capex:,.0f}</div>
                    <div class="econ-label">💵 Capital Cost</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="econ-card lcoe">
                    <div class="econ-value">{lcoe_val*100:.2f} ¢/kWh</div>
                    <div class="econ-label">⚡ Levelized Cost</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="econ-card reliability">
                    <div class="econ-value">{sim['reliability']:.1f}%</div>
                    <div class="econ-label">✅ Reliability</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write("")
            
            # Charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                solar_pct = sim['Epv'] / (sim['Epv'] + sim['Ew']) * 100 if (sim['Epv'] + sim['Ew']) > 0 else 50
                wind_pct = 100 - solar_pct
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['Solar', 'Wind'],
                    values=[sim['Epv'], sim['Ew']],
                    hole=0.6,
                    marker=dict(colors=['#f59e0b', '#3b82f6']),
                    textinfo='percent',
                    textfont=dict(size=14, color='white')
                )])
                fig_pie.update_layout(
                    title=dict(text="Energy Mix", font=dict(size=16, color='white')),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=300,
                    margin=dict(t=50, b=20, l=20, r=20),
                    legend=dict(font=dict(color='white'))
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                fig_conv = go.Figure()
                fig_conv.add_trace(go.Scatter(
                    y=[h*100 for h in result['history']],
                    mode='lines',
                    line=dict(color='#00d4ff', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(0, 212, 255, 0.1)'
                ))
                fig_conv.update_layout(
                    title=dict(text="Convergence", font=dict(size=16, color='white')),
                    xaxis=dict(title="Iteration", color='white', gridcolor='rgba(255,255,255,0.1)'),
                    yaxis=dict(title="LCOE (¢/kWh)", color='white', gridcolor='rgba(255,255,255,0.1)'),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=300,
                    margin=dict(t=50, b=40, l=40, r=20)
                )
                st.plotly_chart(fig_conv, use_container_width=True)
            
            st.divider()
    
    # Tab 2: Analysis
    with tab2:
        if len(selected_sites) > 1 and all_results:
            st.markdown("### 📊 Multi-Site Comparison")
            
            comparison_data = []
            for site_name in selected_sites:
                if site_name in all_results:
                    result = all_results[site_name]['best']
                    df = all_results[site_name]['df']
                    sol = result['solution']
                    sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values,
                                   sol[0], sol[1], sol[2], create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5))
                    lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim['Eserved'], cost_pv, cost_wind, cost_batt)
                    
                    comparison_data.append({
                        'Site': site_name,
                        'Climate': MOROCCO_SITES[site_name]['climate'],
                        'GHI': int(df['GHI'].sum()/1000),
                        'Wind': round(df['wind_speed'].mean(), 1),
                        'PV (kW)': round(sol[0], 1),
                        'Battery (kWh)': round(sol[2], 1),
                        'CAPEX ($)': int(capex),
                        'LCOE (¢/kWh)': round(lcoe_val*100, 2)
                    })
            
            if comparison_data:
                df_comp = pd.DataFrame(comparison_data)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
                
                # Charts
                fig = make_subplots(rows=1, cols=2, subplot_titles=('LCOE by Site', 'CAPEX by Site'))
                
                colors = [MOROCCO_SITES[s]['color'] for s in df_comp['Site']]
                
                fig.add_trace(go.Bar(x=df_comp['Site'], y=df_comp['LCOE (¢/kWh)'], marker_color=colors), row=1, col=1)
                fig.add_trace(go.Bar(x=df_comp['Site'], y=df_comp['CAPEX ($)'], marker_color=colors), row=1, col=2)
                
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
                fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
                st.plotly_chart(fig, use_container_width=True)
        
        elif len(selected_sites) == 1 and all_results:
            site_name = selected_sites[0]
            if site_name in all_results:
                df = all_results[site_name]['df']
                
                st.markdown("### 📅 Monthly Resource Analysis")
                
                df['month'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M').dt.month
                monthly_ghi = df.groupby('month')['GHI'].sum() / 1000
                monthly_wind = df.groupby('month')['wind_speed'].mean()
                
                fig = make_subplots(rows=1, cols=2, subplot_titles=('Monthly Solar Irradiation', 'Monthly Wind Speed'))
                
                fig.add_trace(go.Bar(x=monthly_ghi.index, y=monthly_ghi.values, marker_color='#f59e0b'), row=1, col=1)
                fig.add_trace(go.Bar(x=monthly_wind.index, y=monthly_wind.values, marker_color='#3b82f6'), row=1, col=2)
                
                fig.update_layout(
                    height=350,
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                fig.update_xaxes(title_text="Month", gridcolor='rgba(255,255,255,0.1)')
                fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: Dispatch
    with tab3:
        if all_results:
            site_name = selected_sites[0]
            if site_name in all_results:
                df = all_results[site_name]['df']
                result = all_results[site_name]['best']
                sol = result['solution']
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values, sol[0], sol[1], sol[2], load_profile)
                
                st.markdown("### ⚡ Hourly Power Dispatch (Sample Week)")
                
                hours = list(range(168))
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hours, y=sim['pv'][:168], name='PV', fill='tozeroy', 
                                        line=dict(color='#f59e0b'), fillcolor='rgba(245, 158, 11, 0.3)'))
                fig.add_trace(go.Scatter(x=hours, y=sim['wind'][:168], name='Wind', fill='tozeroy',
                                        line=dict(color='#3b82f6'), fillcolor='rgba(59, 130, 246, 0.3)'))
                fig.add_trace(go.Scatter(x=hours, y=load_profile[:168], name='Load',
                                        line=dict(color='#ef4444', width=2, dash='dash')))
                
                fig.update_layout(
                    xaxis_title="Hour",
                    yaxis_title="Power (kW)",
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color='white'))
                )
                fig.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
                fig.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("### 🔋 Battery State of Charge")
                
                fig_soc = go.Figure()
                fig_soc.add_trace(go.Scatter(x=hours, y=sim['soc'][:168]*100, name='SoC',
                                            line=dict(color='#10b981', width=2),
                                            fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.2)'))
                fig_soc.add_hline(y=20, line_dash="dash", line_color="#ef4444", 
                                 annotation_text="Min SoC (20%)", annotation_font_color="white")
                fig_soc.update_layout(
                    xaxis_title="Hour",
                    yaxis_title="State of Charge (%)",
                    height=300,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                fig_soc.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
                fig_soc.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
                st.plotly_chart(fig_soc, use_container_width=True)
    
    # Tab 4: Export
    with tab4:
        st.markdown("### 📥 Export Results")
        
        export_data = []
        for site_name in selected_sites:
            if site_name in all_results:
                result = all_results[site_name]['best']
                df = all_results[site_name]['df']
                sol = result['solution']
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values, sol[0], sol[1], sol[2], load_profile)
                lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim['Eserved'], cost_pv, cost_wind, cost_batt)
                
                export_data.append({
                    'Site': site_name,
                    'Algorithm': result['algorithm'],
                    'Load Type': load_type,
                    'PV (kW)': round(sol[0], 2),
                    'Wind (kW)': round(sol[1], 2),
                    'Battery (kWh)': round(sol[2], 2),
                    'CAPEX ($)': round(capex, 2),
                    'LCOE (¢/kWh)': round(lcoe_val*100, 2),
                    'Reliability (%)': round(sim['reliability'], 2)
                })
        
        if export_data:
            df_export = pd.DataFrame(export_data)
            st.dataframe(df_export, use_container_width=True, hide_index=True)
            
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Results (CSV)",
                data=csv,
                file_name="hres_optimization_results.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    # Welcome Screen
    st.markdown("""
    <div class="welcome-card">
        <div class="welcome-icon">🌍</div>
        <div class="welcome-title">Welcome to HRES Optimizer</div>
        <div class="welcome-text">
            Configure your parameters in the sidebar and click <strong>OPTIMIZE</strong> to find the optimal 
            hybrid renewable energy system sizing for your selected Moroccan location.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">📍</div>
            <div class="feature-title">8 Sites</div>
            <div class="feature-desc">Moroccan locations</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">3 Algorithms</div>
            <div class="feature-desc">PSO, GA, GWO</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">2 Load Types</div>
            <div class="feature-desc">Fixed & Variable</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Real Data</div>
            <div class="feature-desc">PVGIS 2005-2023</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sites Map
    st.markdown("### 🗺️ Available Sites")
    
    map_data = []
    for site_name, info in MOROCCO_SITES.items():
        if site_name != "Custom":
            map_data.append({'lat': info['lat'], 'lon': info['lon'], 'site': site_name})
    
    df_map = pd.DataFrame(map_data)
    st.map(df_map, latitude='lat', longitude='lon', size=100)
    
    # Sites Info
    col1, col2, col3, col4 = st.columns(4)
    sites_list = list(MOROCCO_SITES.items())
    for idx, (name, info) in enumerate(sites_list[:8]):
        if name != "Custom":
            with [col1, col2, col3, col4][idx % 4]:
                st.markdown(f"""
                <div class="site-card">
                    <div class="site-icon">{info['icon']}</div>
                    <div class="site-name">{name}</div>
                    <div class="site-climate">{info['climate']}</div>
                </div>
                """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <div class="footer-text">
        🔬 <strong>HRES Optimizer Morocco</strong> | 
        Powered by PVGIS Data | © 2025
    </div>
</div>
""", unsafe_allow_html=True)

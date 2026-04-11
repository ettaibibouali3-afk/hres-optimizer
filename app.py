import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="HRES Optimizer - Off-Grid PV-Wind-Battery Systems",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SESSION STATE
# ============================================================
if "all_results" not in st.session_state:
    st.session_state.all_results = {}
if "has_run" not in st.session_state:
    st.session_state.has_run = False
if "cached_params" not in st.session_state:
    st.session_state.cached_params = {}

# ============================================================
# CSS STYLING
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp { font-family: 'Inter', sans-serif; }
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
    
    .hero-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0c4a6e 100%);
        padding: 2.5rem 2rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        box-shadow: 0 25px 50px rgba(0,0,0,0.4);
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
        line-height: 1.3;
    }
    
    .hero-subtitle {
        font-size: 1.1rem;
        color: #cbd5e1;
        text-align: center;
        font-weight: 400;
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
    
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
        text-align: center;
    }
    
    .metric-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #ffffff; margin-bottom: 0.2rem; }
    .metric-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    
    .result-card {
        background: linear-gradient(145deg, #0f172a, #1e293b);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        border: 1px solid rgba(56, 189, 248, 0.2);
        margin-bottom: 1rem;
    }
    
    .result-title { font-size: 1.5rem; font-weight: 700; color: #38bdf8; }
    
    .system-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        border: 2px solid rgba(56, 189, 248, 0.3);
        margin-bottom: 1.5rem;
    }
    
    .system-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 1rem;
    }
    
    .system-components {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-bottom: 1.5rem;
    }
    
    .component {
        text-align: center;
    }
    
    .component-icon { font-size: 2.5rem; }
    .component-value { font-size: 1.5rem; font-weight: 700; color: #ffffff; }
    .component-label { font-size: 0.75rem; color: #94a3b8; }
    
    .metrics-row {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
    
    .metric-box {
        background: rgba(0,0,0,0.2);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        text-align: center;
        min-width: 100px;
    }
    
    .metric-box-value { font-size: 1.4rem; font-weight: 700; color: #22d3ee; }
    .metric-box-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; }
    
    .diesel-comparison {
        background: linear-gradient(145deg, #14532d, #166534);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        text-align: center;
        margin-top: 1rem;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    
    .diesel-text { color: #86efac; font-weight: 600; font-size: 1rem; }
    
    .recommendation-card {
        background: linear-gradient(145deg, #1e3a5f, #0c4a6e);
        border-radius: 16px;
        padding: 1.5rem;
        border: 2px solid #38bdf8;
        margin: 1.5rem 0;
    }
    
    .recommendation-title {
        font-size: 1rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 0.5rem;
    }
    
    .recommendation-text {
        color: #e2e8f0;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }
    
    .comparison-table th {
        background: linear-gradient(145deg, #1e293b, #334155);
        color: #38bdf8;
        padding: 1rem;
        text-align: center;
        font-weight: 600;
        border: 1px solid rgba(148, 163, 184, 0.2);
    }
    
    .comparison-table td {
        background: rgba(30, 41, 59, 0.5);
        color: #ffffff;
        padding: 0.8rem;
        text-align: center;
        border: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .comparison-table tr:hover td {
        background: rgba(56, 189, 248, 0.1);
    }
    
    .best-value {
        color: #34d399 !important;
        font-weight: 700;
    }
    
    .selected-row {
        background: rgba(56, 189, 248, 0.2) !important;
        border-left: 4px solid #38bdf8 !important;
    }
    
    .priority-icon { font-size: 1.2rem; margin-right: 0.5rem; }
    
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.75rem 2rem !important;
        font-size: 1rem !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3);
    }
    
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
    
    .priority-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(148, 163, 184, 0.1);
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .priority-card:hover {
        border-color: #38bdf8;
        transform: translateX(5px);
    }
    
    .priority-card.selected {
        border-color: #38bdf8;
        background: linear-gradient(145deg, #1e3a5f, #0c4a6e);
    }
    
    .priority-name {
        font-weight: 600;
        color: #ffffff;
        font-size: 0.95rem;
    }
    
    .priority-desc {
        color: #94a3b8;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HERO HEADER
# ============================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">Off-Grid Hybrid PV-Wind-Battery Optimizer</div>
    <div class="hero-subtitle">Intelligent System Sizing for Any Location Worldwide</div>
    <div style="text-align: center;">
        <span class="hero-badge">Free Tool</span>
        <span class="hero-badge">Worldwide</span>
        <span class="hero-badge">PVGIS Data</span>
        <span class="hero-badge">Smart Recommendations</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# PRESET SITES DATA
# ============================================================
PRESET_SITES = {
    # Global South - Paper Sites
    "Dakhla, Morocco": {"lat": 23.72, "lon": -15.93, "climate": "Coastal Desert", "color": "#f59e0b", "diesel_price": 1.10},
    "Cairo, Egypt": {"lat": 30.04, "lon": 31.24, "climate": "Desert", "color": "#eab308", "diesel_price": 0.90},
    "Nairobi, Kenya": {"lat": -1.29, "lon": 36.82, "climate": "Tropical Highland", "color": "#22c55e", "diesel_price": 1.30},
    "Dubai, UAE": {"lat": 25.20, "lon": 55.27, "climate": "Desert", "color": "#f59e0b", "diesel_price": 0.70},
    "Karachi, Pakistan": {"lat": 24.86, "lon": 67.01, "climate": "Arid", "color": "#f97316", "diesel_price": 1.15},
    "Bangkok, Thailand": {"lat": 13.76, "lon": 100.50, "climate": "Tropical", "color": "#22c55e", "diesel_price": 1.05},
    "Santiago, Chile": {"lat": -33.45, "lon": -70.67, "climate": "Mediterranean", "color": "#dc2626", "diesel_price": 1.25},
    "Suva, Fiji": {"lat": -18.14, "lon": 178.44, "climate": "Tropical Oceanic", "color": "#06b6d4", "diesel_price": 1.50},
    # Additional Sites
    "Ouarzazate, Morocco": {"lat": 30.92, "lon": -6.90, "climate": "Desert", "color": "#f59e0b", "diesel_price": 1.10},
    "Marrakech, Morocco": {"lat": 31.63, "lon": -8.01, "climate": "Semi-arid", "color": "#ec4899", "diesel_price": 1.10},
    "Cape Town, South Africa": {"lat": -33.93, "lon": 18.42, "climate": "Mediterranean", "color": "#06b6d4", "diesel_price": 1.20},
    "Lagos, Nigeria": {"lat": 6.52, "lon": 3.38, "climate": "Tropical", "color": "#22c55e", "diesel_price": 0.95},
    "Addis Ababa, Ethiopia": {"lat": 9.03, "lon": 38.74, "climate": "Subtropical Highland", "color": "#10b981", "diesel_price": 1.10},
    "Mumbai, India": {"lat": 19.08, "lon": 72.88, "climate": "Tropical", "color": "#8b5cf6", "diesel_price": 1.20},
    "Jakarta, Indonesia": {"lat": -6.21, "lon": 106.85, "climate": "Tropical", "color": "#22c55e", "diesel_price": 0.85},
    "Manila, Philippines": {"lat": 14.60, "lon": 120.98, "climate": "Tropical", "color": "#3b82f6", "diesel_price": 1.00},
    "Mexico City, Mexico": {"lat": 19.43, "lon": -99.13, "climate": "Subtropical Highland", "color": "#22c55e", "diesel_price": 1.15},
    "Lima, Peru": {"lat": -12.05, "lon": -77.04, "climate": "Desert", "color": "#f59e0b", "diesel_price": 1.10},
    "Bogota, Colombia": {"lat": 4.71, "lon": -74.07, "climate": "Subtropical Highland", "color": "#10b981", "diesel_price": 0.95},
    "Sao Paulo, Brazil": {"lat": -23.55, "lon": -46.63, "climate": "Subtropical", "color": "#eab308", "diesel_price": 1.30},
}

REGIONS = {
    "Global South (Paper Sites)": ["Dakhla, Morocco", "Cairo, Egypt", "Nairobi, Kenya", "Dubai, UAE", "Karachi, Pakistan", "Bangkok, Thailand", "Santiago, Chile", "Suva, Fiji"],
    "Africa": ["Dakhla, Morocco", "Ouarzazate, Morocco", "Marrakech, Morocco", "Cairo, Egypt", "Nairobi, Kenya", "Cape Town, South Africa", "Lagos, Nigeria", "Addis Ababa, Ethiopia"],
    "Asia": ["Dubai, UAE", "Karachi, Pakistan", "Mumbai, India", "Bangkok, Thailand", "Jakarta, Indonesia", "Manila, Philippines"],
    "Latin America": ["Mexico City, Mexico", "Lima, Peru", "Bogota, Colombia", "Sao Paulo, Brazil", "Santiago, Chile"],
    "Pacific": ["Suva, Fiji"],
}

# ============================================================
# SYSTEM PARAMETERS
# ============================================================
SYSTEM_PARAMS = {
    "pv_temp_coeff": -0.004,
    "pv_noct": 45,
    "pv_temp_ref": 25,
    "pv_derate": 0.90,
    "wind_hub_height": 30,
    "wind_ref_height": 10,
    "wind_shear_exp": 0.14,
    "wind_cut_in": 3.0,
    "wind_cut_out": 25.0,
    "wind_rated": 12.0,
    "batt_eff_charge": 0.95,
    "batt_eff_discharge": 0.95,
    "batt_soc_min": 0.20,
    "batt_soc_max": 0.95,
    "batt_soc_init": 0.50,
    "discount_rate": 0.08,
    "project_life": 25,
    "om_rate": 0.015,
    "co2_pv_g_per_kwh": 40,
    "co2_wind_g_per_kwh": 12,
    "co2_batt_g_per_kwh": 50,
    "co2_diesel_g_per_kwh": 800,
}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    # Location Selection
    st.markdown("### 📍 Location")
    site_option = st.radio("Select type:", ["Preset Locations", "Custom Coordinates"], key="site_option", label_visibility="collapsed")
    
    if site_option == "Preset Locations":
        selected_region = st.selectbox("Region:", list(REGIONS.keys()), key="region")
        selected_site = st.selectbox("Site:", REGIONS[selected_region], key="site")
    else:
        custom_lat = st.number_input("Latitude", value=25.0, min_value=-60.0, max_value=70.0, step=0.1)
        custom_lon = st.number_input("Longitude", value=0.0, min_value=-180.0, max_value=180.0, step=0.1)
        custom_name = st.text_input("Location name", value="Custom Location")
        selected_site = custom_name
        PRESET_SITES[custom_name] = {"lat": custom_lat, "lon": custom_lon, "climate": "Custom", "color": "#64748b", "diesel_price": 1.20}
    
    st.divider()
    
    # Load Profile
    st.markdown("### ⚡ Load Profile")
    load_type = st.radio("Load type:", ["Constant Load", "Variable Load"], key="load_type")
    
    if load_type == "Constant Load":
        load_kw = st.slider("Load (kW)", 1, 50, 5, key="load_kw")
    else:
        load_kw = st.slider("Average Load (kW)", 1, 50, 5, key="load_kw_var")
        st.caption("Residential pattern: Peak at morning & evening")
    
    st.divider()
    
    # Priority Selection
    st.markdown("### 🎯 What is your priority?")
    
    priority = st.radio(
        "Select your priority:",
        [
            "💰 Lowest Cost",
            "🔒 Maximum Reliability",
            "🌱 Lowest Environmental Impact",
            "⚖️ Best Overall Balance"
        ],
        key="priority",
        label_visibility="collapsed"
    )
    
    # Priority descriptions
    priority_descriptions = {
        "💰 Lowest Cost": "Minimize electricity cost while meeting 95% reliability",
        "🔒 Maximum Reliability": "Achieve 100% uptime for critical loads",
        "🌱 Lowest Environmental Impact": "Minimize carbon footprint",
        "⚖️ Best Overall Balance": "Optimal trade-off between cost, reliability & emissions"
    }
    st.caption(priority_descriptions[priority])
    
    st.divider()
    
    # Cost Parameters
    st.markdown("### 💵 Component Costs")
    cost_pv = st.slider("PV ($/kW)", 300, 1200, 600, step=50, key="cost_pv")
    cost_wind = st.slider("Wind ($/kW)", 800, 2000, 1200, step=50, key="cost_wind")
    cost_batt = st.slider("Battery ($/kWh)", 150, 500, 250, step=25, key="cost_batt")
    
    st.divider()
    
    # Run Button
    run_optimization = st.button("🚀 OPTIMIZE SYSTEM", type="primary", use_container_width=True)


# ============================================================
# CORE FUNCTIONS
# ============================================================

def create_load_profile(load_type_param, base_load=5):
    """Create hourly load profile for 8760 hours"""
    if load_type_param == "Constant Load":
        return np.full(8760, base_load)
    else:
        # Variable residential pattern
        hourly_pattern = {
            0: 0.4, 1: 0.35, 2: 0.35, 3: 0.35, 4: 0.35, 5: 0.5,
            6: 0.8, 7: 1.2, 8: 1.0, 9: 0.7, 10: 0.6, 11: 0.6,
            12: 0.8, 13: 0.7, 14: 0.6, 15: 0.6, 16: 0.7, 17: 1.0,
            18: 1.4, 19: 1.5, 20: 1.3, 21: 1.1, 22: 0.8, 23: 0.5
        }
        load = np.array([hourly_pattern[h % 24] * base_load for h in range(8760)])
        return load


def simulate_system(ghi, ws, temp, P_pv, P_wind, B_cap, load):
    """Simulate hybrid system for one year"""
    n = len(ghi)
    
    # PV generation with temperature correction
    T_cell = temp + (SYSTEM_PARAMS["pv_noct"] - 20) * ghi / 800
    eta_temp = 1 + SYSTEM_PARAMS["pv_temp_coeff"] * (T_cell - SYSTEM_PARAMS["pv_temp_ref"])
    P_pv_out = P_pv * (ghi / 1000) * eta_temp * SYSTEM_PARAMS["pv_derate"]
    P_pv_out = np.maximum(P_pv_out, 0)
    
    # Wind generation
    ws_hub = ws * (SYSTEM_PARAMS["wind_hub_height"] / SYSTEM_PARAMS["wind_ref_height"]) ** SYSTEM_PARAMS["wind_shear_exp"]
    P_wind_out = np.zeros(n)
    for t in range(n):
        v = ws_hub[t]
        if v < SYSTEM_PARAMS["wind_cut_in"] or v > SYSTEM_PARAMS["wind_cut_out"]:
            P_wind_out[t] = 0
        elif v < SYSTEM_PARAMS["wind_rated"]:
            P_wind_out[t] = P_wind * ((v - SYSTEM_PARAMS["wind_cut_in"]) / 
                                       (SYSTEM_PARAMS["wind_rated"] - SYSTEM_PARAMS["wind_cut_in"])) ** 3
        else:
            P_wind_out[t] = P_wind
    
    P_gen = P_pv_out + P_wind_out
    
    # Battery simulation
    SoC = SYSTEM_PARAMS["batt_soc_init"] * B_cap
    SoC_min = SYSTEM_PARAMS["batt_soc_min"] * B_cap
    SoC_max = SYSTEM_PARAMS["batt_soc_max"] * B_cap
    
    E_served = 0
    E_demand = 0
    soc_history = np.zeros(n)
    
    for t in range(n):
        E_demand += load[t]
        P_net = P_gen[t] - load[t]
        
        if P_net >= 0:
            E_charge = min(P_net * SYSTEM_PARAMS["batt_eff_charge"], SoC_max - SoC)
            SoC += E_charge
            E_served += load[t]
        else:
            E_needed = -P_net
            E_avail = (SoC - SoC_min) * SYSTEM_PARAMS["batt_eff_discharge"]
            E_discharge = min(E_needed, E_avail)
            SoC -= E_discharge / SYSTEM_PARAMS["batt_eff_discharge"]
            E_served += load[t] - (E_needed - E_discharge)
        
        soc_history[t] = SoC / B_cap if B_cap > 0 else 0
    
    E_served = max(E_served, 0)
    lpsp = (E_demand - E_served) / E_demand if E_demand > 0 else 0
    reliability = (1 - lpsp) * 100
    
    E_pv_total = np.sum(P_pv_out)
    E_wind_total = np.sum(P_wind_out)
    
    return {
        "reliability": reliability,
        "lpsp": lpsp,
        "E_served": E_served,
        "E_demand": E_demand,
        "E_pv": E_pv_total,
        "E_wind": E_wind_total,
        "soc_history": soc_history,
        "P_pv_out": P_pv_out,
        "P_wind_out": P_wind_out,
        "P_gen": P_gen
    }


def calc_lcoe(P_pv, P_wind, B_cap, E_served, c_pv, c_wind, c_batt):
    """Calculate Levelized Cost of Energy"""
    capex = P_pv * c_pv + P_wind * c_wind + B_cap * c_batt
    crf = SYSTEM_PARAMS["discount_rate"] * (1 + SYSTEM_PARAMS["discount_rate"])**SYSTEM_PARAMS["project_life"] / \
          ((1 + SYSTEM_PARAMS["discount_rate"])**SYSTEM_PARAMS["project_life"] - 1)
    annual_cost = capex * crf + capex * SYSTEM_PARAMS["om_rate"]
    lcoe = annual_cost / E_served if E_served > 0 else float('inf')
    return lcoe, capex


def calc_co2(P_pv, P_wind, B_cap, E_served):
    """Calculate annual CO2 emissions (kg/year)"""
    # Embodied emissions amortized over project life
    co2_pv = (P_pv * 1000 * SYSTEM_PARAMS["co2_pv_g_per_kwh"]) / SYSTEM_PARAMS["project_life"] / 1000
    co2_wind = (P_wind * 1000 * SYSTEM_PARAMS["co2_wind_g_per_kwh"]) / SYSTEM_PARAMS["project_life"] / 1000
    co2_batt = (B_cap * SYSTEM_PARAMS["co2_batt_g_per_kwh"]) / 12 / 1000  # 12-year battery life
    return co2_pv + co2_wind + co2_batt


def calc_diesel_baseline(E_annual, diesel_price):
    """Calculate diesel generator baseline"""
    diesel_consumption = 0.3  # L/kWh
    diesel_capex_per_kw = 500
    diesel_om_per_kwh = 0.02
    
    # Assume diesel generator sized for peak load
    fuel_cost = E_annual * diesel_consumption * diesel_price
    om_cost = E_annual * diesel_om_per_kwh
    
    # LCOE
    crf = SYSTEM_PARAMS["discount_rate"] * (1 + SYSTEM_PARAMS["discount_rate"])**SYSTEM_PARAMS["project_life"] / \
          ((1 + SYSTEM_PARAMS["discount_rate"])**SYSTEM_PARAMS["project_life"] - 1)
    diesel_lcoe = (fuel_cost + om_cost) / E_annual + diesel_capex_per_kw * crf * 15 / E_annual  # 15 kW genset
    
    # CO2
    diesel_co2 = E_annual * SYSTEM_PARAMS["co2_diesel_g_per_kwh"] / 1000  # kg/year
    
    return {
        "lcoe": diesel_lcoe,
        "co2": diesel_co2,
        "fuel_cost": fuel_cost
    }


# ============================================================
# OPTIMIZATION FUNCTIONS
# ============================================================

def pso_optimize_cost(ghi, ws, temp, load, c_pv, c_wind, c_batt, min_reliability=95.0):
    """PSO to minimize LCOE subject to reliability constraint"""
    np.random.seed(42)
    
    bounds = [(5, 100), (0, 50), (20, 500)]  # PV, Wind, Battery
    n_particles = 30
    n_iterations = 60
    
    # Initialize particles
    particles = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_particles)])
    velocities = np.zeros_like(particles)
    
    pbest = particles.copy()
    pbest_fitness = np.full(n_particles, np.inf)
    gbest = None
    gbest_fitness = np.inf
    
    for iteration in range(n_iterations):
        for i in range(n_particles):
            P_pv, P_wind, B_cap = particles[i]
            
            # Simulate
            sim = simulate_system(ghi, ws, temp, P_pv, P_wind, B_cap, load)
            lcoe, capex = calc_lcoe(P_pv, P_wind, B_cap, sim["E_served"], c_pv, c_wind, c_batt)
            
            # Fitness with penalty
            if sim["reliability"] >= min_reliability:
                fitness = lcoe
            else:
                fitness = lcoe + 10 * (min_reliability - sim["reliability"])
            
            # Update personal best
            if fitness < pbest_fitness[i]:
                pbest_fitness[i] = fitness
                pbest[i] = particles[i].copy()
                
                # Update global best
                if fitness < gbest_fitness:
                    gbest_fitness = fitness
                    gbest = particles[i].copy()
        
        # Update velocities and positions
        w = 0.7 - 0.4 * (iteration / n_iterations)
        c1, c2 = 1.5, 1.5
        
        for i in range(n_particles):
            r1, r2 = np.random.rand(3), np.random.rand(3)
            velocities[i] = w * velocities[i] + c1 * r1 * (pbest[i] - particles[i]) + c2 * r2 * (gbest - particles[i])
            particles[i] = particles[i] + velocities[i]
            
            # Clip to bounds
            for d in range(3):
                particles[i, d] = np.clip(particles[i, d], bounds[d][0], bounds[d][1])
    
    return gbest


def pso_optimize_reliability(ghi, ws, temp, load, c_pv, c_wind, c_batt):
    """PSO to maximize reliability (no cost constraint)"""
    np.random.seed(43)
    
    bounds = [(10, 150), (0, 80), (50, 800)]  # Larger bounds for max reliability
    n_particles = 30
    n_iterations = 60
    
    particles = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_particles)])
    velocities = np.zeros_like(particles)
    
    pbest = particles.copy()
    pbest_fitness = np.full(n_particles, -np.inf)
    gbest = None
    gbest_fitness = -np.inf
    
    for iteration in range(n_iterations):
        for i in range(n_particles):
            P_pv, P_wind, B_cap = particles[i]
            sim = simulate_system(ghi, ws, temp, P_pv, P_wind, B_cap, load)
            
            # Maximize reliability
            fitness = sim["reliability"]
            
            if fitness > pbest_fitness[i]:
                pbest_fitness[i] = fitness
                pbest[i] = particles[i].copy()
                
                if fitness > gbest_fitness:
                    gbest_fitness = fitness
                    gbest = particles[i].copy()
        
        w = 0.7 - 0.4 * (iteration / n_iterations)
        c1, c2 = 1.5, 1.5
        
        for i in range(n_particles):
            r1, r2 = np.random.rand(3), np.random.rand(3)
            velocities[i] = w * velocities[i] + c1 * r1 * (pbest[i] - particles[i]) + c2 * r2 * (gbest - particles[i])
            particles[i] = particles[i] + velocities[i]
            
            for d in range(3):
                particles[i, d] = np.clip(particles[i, d], bounds[d][0], bounds[d][1])
    
    return gbest


def pso_optimize_co2(ghi, ws, temp, load, c_pv, c_wind, c_batt, min_reliability=95.0):
    """PSO to minimize CO2 subject to reliability constraint"""
    np.random.seed(44)
    
    bounds = [(5, 100), (0, 50), (20, 500)]
    n_particles = 30
    n_iterations = 60
    
    particles = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_particles)])
    velocities = np.zeros_like(particles)
    
    pbest = particles.copy()
    pbest_fitness = np.full(n_particles, np.inf)
    gbest = None
    gbest_fitness = np.inf
    
    for iteration in range(n_iterations):
        for i in range(n_particles):
            P_pv, P_wind, B_cap = particles[i]
            
            sim = simulate_system(ghi, ws, temp, P_pv, P_wind, B_cap, load)
            co2 = calc_co2(P_pv, P_wind, B_cap, sim["E_served"])
            
            if sim["reliability"] >= min_reliability:
                fitness = co2
            else:
                fitness = co2 + 100 * (min_reliability - sim["reliability"])
            
            if fitness < pbest_fitness[i]:
                pbest_fitness[i] = fitness
                pbest[i] = particles[i].copy()
                
                if fitness < gbest_fitness:
                    gbest_fitness = fitness
                    gbest = particles[i].copy()
        
        w = 0.7 - 0.4 * (iteration / n_iterations)
        c1, c2 = 1.5, 1.5
        
        for i in range(n_particles):
            r1, r2 = np.random.rand(3), np.random.rand(3)
            velocities[i] = w * velocities[i] + c1 * r1 * (pbest[i] - particles[i]) + c2 * r2 * (gbest - particles[i])
            particles[i] = particles[i] + velocities[i]
            
            for d in range(3):
                particles[i, d] = np.clip(particles[i, d], bounds[d][0], bounds[d][1])
    
    return gbest


def nsga2_optimize(ghi, ws, temp, load, c_pv, c_wind, c_batt, n_pop=50, n_gen=60):
    """NSGA-II for multi-objective optimization (LCOE, Reliability, CO2)"""
    np.random.seed(45)
    
    bounds = [(5, 120), (0, 60), (20, 600)]
    
    def evaluate(x):
        P_pv, P_wind, B_cap = x
        sim = simulate_system(ghi, ws, temp, P_pv, P_wind, B_cap, load)
        lcoe, _ = calc_lcoe(P_pv, P_wind, B_cap, sim["E_served"], c_pv, c_wind, c_batt)
        co2 = calc_co2(P_pv, P_wind, B_cap, sim["E_served"])
        return [lcoe, -sim["reliability"], co2]  # Minimize all (negate reliability)
    
    def dominates(a, b):
        return all(a[i] <= b[i] for i in range(3)) and any(a[i] < b[i] for i in range(3))
    
    def non_dominated_sort(pop, fitness):
        n = len(pop)
        fronts = [[]]
        domination_count = np.zeros(n)
        dominated_set = [[] for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    if dominates(fitness[i], fitness[j]):
                        dominated_set[i].append(j)
                    elif dominates(fitness[j], fitness[i]):
                        domination_count[i] += 1
            
            if domination_count[i] == 0:
                fronts[0].append(i)
        
        k = 0
        while fronts[k]:
            next_front = []
            for i in fronts[k]:
                for j in dominated_set[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        next_front.append(j)
            k += 1
            fronts.append(next_front)
        
        return fronts[:-1]
    
    def crowding_distance(fitness, front):
        n = len(front)
        if n <= 2:
            return [float('inf')] * n
        
        distances = [0] * n
        for m in range(3):
            sorted_idx = sorted(range(n), key=lambda i: fitness[front[i]][m])
            distances[sorted_idx[0]] = float('inf')
            distances[sorted_idx[-1]] = float('inf')
            
            f_range = fitness[front[sorted_idx[-1]]][m] - fitness[front[sorted_idx[0]]][m]
            if f_range > 0:
                for i in range(1, n - 1):
                    distances[sorted_idx[i]] += (fitness[front[sorted_idx[i + 1]]][m] - 
                                                  fitness[front[sorted_idx[i - 1]]][m]) / f_range
        
        return distances
    
    # Initialize population
    pop = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_pop)])
    
    for gen in range(n_gen):
        # Evaluate
        fitness = [evaluate(ind) for ind in pop]
        
        # Non-dominated sort
        fronts = non_dominated_sort(pop, fitness)
        
        # Create offspring
        offspring = []
        while len(offspring) < n_pop:
            # Tournament selection
            i, j = np.random.randint(0, n_pop, 2)
            parent1 = pop[i] if fitness[i][0] < fitness[j][0] else pop[j]
            
            i, j = np.random.randint(0, n_pop, 2)
            parent2 = pop[i] if fitness[i][0] < fitness[j][0] else pop[j]
            
            # Crossover
            if np.random.rand() < 0.9:
                alpha = np.random.rand(3)
                child = alpha * parent1 + (1 - alpha) * parent2
            else:
                child = parent1.copy()
            
            # Mutation
            if np.random.rand() < 0.1:
                d = np.random.randint(0, 3)
                child[d] = np.random.uniform(bounds[d][0], bounds[d][1])
            
            # Clip
            for d in range(3):
                child[d] = np.clip(child[d], bounds[d][0], bounds[d][1])
            
            offspring.append(child)
        
        offspring = np.array(offspring)
        
        # Combine and select
        combined = np.vstack([pop, offspring])
        combined_fitness = [evaluate(ind) for ind in combined]
        fronts = non_dominated_sort(combined, combined_fitness)
        
        new_pop = []
        for front in fronts:
            if len(new_pop) + len(front) <= n_pop:
                new_pop.extend([combined[i] for i in front])
            else:
                distances = crowding_distance(combined_fitness, front)
                sorted_front = sorted(zip(front, distances), key=lambda x: -x[1])
                for i, _ in sorted_front[:n_pop - len(new_pop)]:
                    new_pop.append(combined[i])
                break
        
        pop = np.array(new_pop)
    
    # Get Pareto front
    fitness = [evaluate(ind) for ind in pop]
    fronts = non_dominated_sort(pop, fitness)
    pareto_front = [pop[i] for i in fronts[0]]
    pareto_fitness = [fitness[i] for i in fronts[0]]
    
    # Find knee point
    def find_knee_point(pareto, pareto_fit):
        if len(pareto) == 0:
            return pareto[0]
        
        # Normalize objectives
        fit_array = np.array(pareto_fit)
        fit_min = fit_array.min(axis=0)
        fit_max = fit_array.max(axis=0)
        fit_range = fit_max - fit_min
        fit_range[fit_range == 0] = 1
        
        fit_norm = (fit_array - fit_min) / fit_range
        
        # Find point with minimum distance to ideal
        distances = np.sqrt(np.sum(fit_norm ** 2, axis=1))
        knee_idx = np.argmin(distances)
        
        return pareto[knee_idx]
    
    knee_point = find_knee_point(pareto_front, pareto_fitness)
    
    return knee_point, pareto_front, pareto_fitness


@st.cache_data(ttl=3600)
def fetch_pvgis_data(lat, lon):
    """Fetch TMY data from PVGIS API"""
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {
        "lat": lat,
        "lon": lon,
        "outputformat": "json",
        "usehorizon": 1,
        "startyear": 2005,
        "endyear": 2023
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data["outputs"]["tmy_hourly"])
        df = df.rename(columns={
            "G(h)": "GHI",
            "T2m": "temp",
            "WS10m": "wind_speed"
        })
        df["wind_speed"] = df["wind_speed"].clip(lower=0)
        
        return df
    except Exception as e:
        st.error(f"Error fetching PVGIS data: {e}")
        return None


def generate_recommendation(results, selected_priority):
    """Generate smart recommendation text"""
    cost_lcoe = results["💰 Lowest Cost"]["lcoe"] * 100
    balanced_lcoe = results["⚖️ Best Overall Balance"]["lcoe"] * 100
    balanced_rel = results["⚖️ Best Overall Balance"]["reliability"]
    cost_rel = results["💰 Lowest Cost"]["reliability"]
    
    cost_diff_pct = ((balanced_lcoe - cost_lcoe) / cost_lcoe) * 100
    rel_gain = balanced_rel - cost_rel
    
    if selected_priority == "💰 Lowest Cost":
        if rel_gain > 2:
            return f"💡 **Tip:** For just {cost_diff_pct:.0f}% more cost, you could achieve {balanced_rel:.1f}% reliability with the Balanced option."
        else:
            return f"✅ **Good choice!** This is the most economical solution meeting your 95% reliability target."
    
    elif selected_priority == "🔒 Maximum Reliability":
        rel_lcoe = results["🔒 Maximum Reliability"]["lcoe"] * 100
        premium = ((rel_lcoe - cost_lcoe) / cost_lcoe) * 100
        return f"✅ **Maximum protection!** You're paying {premium:.0f}% premium for 100% uptime - worth it for critical loads."
    
    elif selected_priority == "🌱 Lowest Environmental Impact":
        green_co2 = results["🌱 Lowest Environmental Impact"]["co2"]
        cost_co2 = results["💰 Lowest Cost"]["co2"]
        co2_savings = ((cost_co2 - green_co2) / cost_co2) * 100
        return f"🌍 **Eco-friendly choice!** This reduces emissions by {co2_savings:.0f}% compared to the cost-optimized option."
    
    else:  # Balanced
        return f"⚖️ **Smart choice!** You get {balanced_rel:.1f}% reliability at only {cost_diff_pct:.0f}% more cost than the cheapest option."


# ============================================================
# MAIN APP LOGIC
# ============================================================

if run_optimization:
    site_info = PRESET_SITES[selected_site]
    
    st.markdown(f"""
    <div class="result-card">
        <div class="result-title">📍 {selected_site}</div>
        <p style="color: #94a3b8; margin: 0;">Climate: {site_info['climate']} | Lat: {site_info['lat']:.2f}° | Lon: {site_info['lon']:.2f}°</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Fetch data
    with st.spinner("🌐 Fetching solar and wind data from PVGIS..."):
        df = fetch_pvgis_data(site_info["lat"], site_info["lon"])
    
    if df is None:
        st.error("Could not fetch data. Please try again.")
        st.stop()
    
    # Show resource summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">☀️</div><div class="metric-value">{df["GHI"].sum()/1000:.0f}</div><div class="metric-label">kWh/m²/year</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">💨</div><div class="metric-value">{df["wind_speed"].mean():.1f}</div><div class="metric-label">m/s avg wind</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-icon">🌡️</div><div class="metric-value">{df["temp"].mean():.1f}°</div><div class="metric-label">avg temp</div></div>', unsafe_allow_html=True)
    with col4:
        annual_load = load_kw * 8760 if load_type == "Constant Load" else load_kw * 8760
        st.markdown(f'<div class="metric-card"><div class="metric-icon">⚡</div><div class="metric-value">{annual_load/1000:.1f}</div><div class="metric-label">MWh/year load</div></div>', unsafe_allow_html=True)
    
    st.write("")
    
    # Prepare data
    ghi = df["GHI"].values
    ws = df["wind_speed"].values
    temp = df["temp"].values
    load_profile = create_load_profile(load_type, load_kw)
    E_annual = np.sum(load_profile)
    
    # Run ALL optimizations
    with st.spinner("🔄 Running optimization for all priorities..."):
        progress = st.progress(0)
        
        # 1. Lowest Cost
        sol_cost = pso_optimize_cost(ghi, ws, temp, load_profile, cost_pv, cost_wind, cost_batt)
        progress.progress(25)
        
        # 2. Maximum Reliability
        sol_rel = pso_optimize_reliability(ghi, ws, temp, load_profile, cost_pv, cost_wind, cost_batt)
        progress.progress(50)
        
        # 3. Lowest Emissions
        sol_co2 = pso_optimize_co2(ghi, ws, temp, load_profile, cost_pv, cost_wind, cost_batt)
        progress.progress(75)
        
        # 4. Balanced (NSGA-II)
        sol_balanced, pareto_front, pareto_fitness = nsga2_optimize(ghi, ws, temp, load_profile, cost_pv, cost_wind, cost_batt)
        progress.progress(100)
    
    # Calculate results for all options
    results = {}
    
    for name, sol in [("💰 Lowest Cost", sol_cost), 
                       ("🔒 Maximum Reliability", sol_rel),
                       ("🌱 Lowest Environmental Impact", sol_co2),
                       ("⚖️ Best Overall Balance", sol_balanced)]:
        sim = simulate_system(ghi, ws, temp, sol[0], sol[1], sol[2], load_profile)
        lcoe, capex = calc_lcoe(sol[0], sol[1], sol[2], sim["E_served"], cost_pv, cost_wind, cost_batt)
        co2 = calc_co2(sol[0], sol[1], sol[2], sim["E_served"])
        
        results[name] = {
            "P_pv": sol[0],
            "P_wind": sol[1],
            "B_cap": sol[2],
            "lcoe": lcoe,
            "capex": capex,
            "reliability": sim["reliability"],
            "co2": co2,
            "sim": sim
        }
    
    # Diesel baseline
    diesel = calc_diesel_baseline(E_annual, site_info.get("diesel_price", 1.20))
    
    # Get selected priority result
    selected_result = results[priority]
    
    # Display selected system
    st.markdown("---")
    st.markdown(f"### ✅ Your Optimal System ({priority})")
    
    st.markdown(f"""
    <div class="system-card">
        <div style="display: flex; justify-content: center; gap: 3rem; margin-bottom: 1.5rem;">
            <div class="component">
                <div class="component-icon">☀️</div>
                <div class="component-value">{selected_result['P_pv']:.1f} kW</div>
                <div class="component-label">Solar PV</div>
            </div>
            <div class="component">
                <div class="component-icon">💨</div>
                <div class="component-value">{selected_result['P_wind']:.1f} kW</div>
                <div class="component-label">Wind</div>
            </div>
            <div class="component">
                <div class="component-icon">🔋</div>
                <div class="component-value">{selected_result['B_cap']:.0f} kWh</div>
                <div class="component-label">Battery</div>
            </div>
        </div>
        <div class="metrics-row">
            <div class="metric-box">
                <div class="metric-box-value">{selected_result['lcoe']*100:.1f}¢</div>
                <div class="metric-box-label">LCOE/kWh</div>
            </div>
            <div class="metric-box">
                <div class="metric-box-value">{selected_result['reliability']:.1f}%</div>
                <div class="metric-box-label">Reliability</div>
            </div>
            <div class="metric-box">
                <div class="metric-box-value">${selected_result['capex']/1000:.1f}K</div>
                <div class="metric-box-label">CAPEX</div>
            </div>
            <div class="metric-box">
                <div class="metric-box-value">{selected_result['co2']:.1f}t</div>
                <div class="metric-box-label">CO₂/year</div>
            </div>
        </div>
        <div class="diesel-comparison">
            <div class="diesel-text">
                📊 vs Diesel: {((diesel['lcoe'] - selected_result['lcoe']) / diesel['lcoe'] * 100):.0f}% cheaper | 
                {((diesel['co2'] - selected_result['co2']) / diesel['co2'] * 100):.0f}% less CO₂ | 
                ${diesel['fuel_cost'] - (selected_result['lcoe'] * E_annual):.0f}/year saved
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Smart recommendation
    recommendation = generate_recommendation(results, priority)
    st.markdown(f"""
    <div class="recommendation-card">
        <div class="recommendation-text">{recommendation}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Comparison table
    st.markdown("### 📊 Compare All Options")
    
    # Find best values for highlighting
    best_lcoe = min(r["lcoe"] for r in results.values())
    best_rel = max(r["reliability"] for r in results.values())
    best_co2 = min(r["co2"] for r in results.values())
    
    comparison_data = []
    for name, r in results.items():
        is_selected = name == priority
        comparison_data.append({
            "Priority": name,
            "PV (kW)": f"{r['P_pv']:.1f}",
            "Wind (kW)": f"{r['P_wind']:.1f}",
            "Battery (kWh)": f"{r['B_cap']:.0f}",
            "LCOE (¢/kWh)": f"{r['lcoe']*100:.1f}" + (" ⭐" if r['lcoe'] == best_lcoe else ""),
            "Reliability (%)": f"{r['reliability']:.1f}" + (" ⭐" if r['reliability'] == best_rel else ""),
            "CO₂ (t/yr)": f"{r['co2']:.1f}" + (" ⭐" if r['co2'] == best_co2 else ""),
            "CAPEX ($)": f"${r['capex']:,.0f}",
            "Selected": "✓" if is_selected else ""
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    st.dataframe(
        df_comparison,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Priority": st.column_config.TextColumn("Priority", width="large"),
            "Selected": st.column_config.TextColumn("", width="small")
        }
    )
    
    # Charts
    st.markdown("### 📈 Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Energy mix pie chart
        sim = selected_result["sim"]
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Solar PV", "Wind"],
            values=[sim["E_pv"], sim["E_wind"]],
            hole=0.6,
            marker=dict(colors=["#f59e0b", "#3b82f6"]),
            textinfo="percent+label"
        )])
        fig_pie.update_layout(
            title="Energy Generation Mix",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=350,
            showlegend=False
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Comparison bar chart
        priorities = ["💰 Cost", "🔒 Reliable", "🌱 Green", "⚖️ Balanced"]
        lcoe_values = [results[k]["lcoe"]*100 for k in results.keys()]
        
        fig_bar = go.Figure(data=[
            go.Bar(
                x=priorities,
                y=lcoe_values,
                marker_color=["#22c55e", "#ef4444", "#3b82f6", "#a855f7"],
                text=[f"{v:.1f}¢" for v in lcoe_values],
                textposition="outside"
            )
        ])
        fig_bar.update_layout(
            title="LCOE Comparison",
            yaxis_title="LCOE (¢/kWh)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            height=350
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Weekly dispatch
    st.markdown("### ⚡ Sample Week Power Dispatch")
    
    hours = list(range(168))
    sim = selected_result["sim"]
    
    fig_dispatch = go.Figure()
    fig_dispatch.add_trace(go.Scatter(
        x=hours, y=sim["P_pv_out"][:168],
        name="Solar PV", fill="tozeroy",
        line=dict(color="#f59e0b"), fillcolor="rgba(245,158,11,0.3)"
    ))
    fig_dispatch.add_trace(go.Scatter(
        x=hours, y=sim["P_wind_out"][:168],
        name="Wind", fill="tozeroy",
        line=dict(color="#3b82f6"), fillcolor="rgba(59,130,246,0.3)"
    ))
    fig_dispatch.add_trace(go.Scatter(
        x=hours, y=load_profile[:168],
        name="Load", line=dict(color="#ef4444", width=2, dash="dash")
    ))
    fig_dispatch.update_layout(
        xaxis_title="Hour of Week",
        yaxis_title="Power (kW)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=400,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_dispatch, use_container_width=True)
    
    # Export
    st.markdown("### 📥 Export Results")
    
    export_data = {
        "Site": selected_site,
        "Priority": priority,
        "PV_kW": selected_result["P_pv"],
        "Wind_kW": selected_result["P_wind"],
        "Battery_kWh": selected_result["B_cap"],
        "LCOE_cents_per_kWh": selected_result["lcoe"] * 100,
        "Reliability_percent": selected_result["reliability"],
        "CO2_tons_per_year": selected_result["co2"],
        "CAPEX_USD": selected_result["capex"],
        "vs_Diesel_cost_savings_percent": ((diesel['lcoe'] - selected_result['lcoe']) / diesel['lcoe'] * 100),
        "vs_Diesel_CO2_savings_percent": ((diesel['co2'] - selected_result['co2']) / diesel['co2'] * 100)
    }
    
    df_export = pd.DataFrame([export_data])
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Results (CSV)",
            df_export.to_csv(index=False),
            f"hres_results_{selected_site.replace(', ', '_')}.csv",
            "text/csv",
            use_container_width=True
        )

else:
    # Welcome screen
    st.markdown("""
    <div class="welcome-card">
        <div class="welcome-icon">🌍</div>
        <div class="welcome-title">Welcome to HRES Optimizer</div>
        <div class="welcome-text">
            Design optimal off-grid hybrid renewable energy systems for any location worldwide.
            <br><br>
            Simply select your location, load profile, and priority in the sidebar, then click <strong>OPTIMIZE</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">🎯</div>
            <div class="feature-title">4 Priorities</div>
            <div class="feature-desc">Cost, Reliability, Environment, or Balanced</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🌍</div>
            <div class="feature-title">20+ Sites</div>
            <div class="feature-desc">Global South Focus</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Real Data</div>
            <div class="feature-desc">PVGIS 2005-2023</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">💡</div>
            <div class="feature-title">Smart Tips</div>
            <div class="feature-desc">Actionable Recommendations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Map
    st.markdown("### 📍 Available Locations")
    map_data = pd.DataFrame([
        {"lat": info["lat"], "lon": info["lon"], "name": name}
        for name, info in PRESET_SITES.items()
    ])
    st.map(map_data, latitude="lat", longitude="lon", size=50)

# Footer
st.markdown("""
<div class="footer">
    <div class="footer-text">
        🔬 Research Tool | Powered by PVGIS Data | © 2026 Dr. Bouali Ettaibi
    </div>
</div>
""", unsafe_allow_html=True)

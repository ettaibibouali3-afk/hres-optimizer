import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="HRES Optimizer - Morocco",
    page_icon="⚡",
    layout="wide"
)

# ============================================================
# TITLE
# ============================================================
st.title("⚡ Hybrid Renewable Energy System Optimizer")
st.markdown("**Optimal sizing of off-grid PV-Wind-Battery systems for Morocco**")
st.markdown("---")

# ============================================================
# SIDEBAR - INPUTS
# ============================================================
st.sidebar.header("📍 System Parameters")

location_options = {
    "Ouarzazate (Desert)": (30.92, -6.90),
    "Dakhla (Coastal)": (23.72, -15.93),
    "Tangier (Mediterranean)": (35.78, -5.81),
    "Ifrane (Mountain)": (33.53, -5.11),
    "Custom Location": None
}

selected_location = st.sidebar.selectbox("Select Location", list(location_options.keys()))

if selected_location == "Custom Location":
    lat = st.sidebar.number_input("Latitude", value=31.63, min_value=20.0, max_value=36.0)
    lon = st.sidebar.number_input("Longitude", value=-8.01, min_value=-17.0, max_value=-1.0)
else:
    lat, lon = location_options[selected_location]
    st.sidebar.info(f"Coordinates: {lat}N, {lon}W")

load_kw = st.sidebar.slider("Load Demand (kW)", min_value=1, max_value=50, value=5)
lpsp_target = st.sidebar.slider("Max LPSP (%)", min_value=1, max_value=20, value=5) / 100

st.sidebar.header("Cost Parameters ($/unit)")
cost_pv = st.sidebar.number_input("PV Cost ($/kW)", value=800, step=50)
cost_wind = st.sidebar.number_input("Wind Cost ($/kW)", value=1200, step=50)
cost_batt = st.sidebar.number_input("Battery Cost ($/kWh)", value=300, step=25)

# ============================================================
# MODELS
# ============================================================
def pv_power(ghi, temp, P_rated, NOCT=45, alpha_p=-0.4, eta_d=0.90):
    G_STC, T_STC = 1000, 25
    T_cell = temp + (NOCT - 20) * (ghi / 800)
    temp_factor = 1 + (alpha_p / 100) * (T_cell - T_STC)
    P_pv = P_rated * (ghi / G_STC) * temp_factor * eta_d
    return np.clip(P_pv, 0, P_rated)

def wind_power(wind_speed, P_rated, hub_height=30, rotor_diameter=20,
               v_cutin=3, v_cutout=25, ref_height=10, alpha=0.14,
               rho=1.225, Cp=0.40, eta_mech=0.95, eta_elec=0.95):
    v_hub = wind_speed * (hub_height / ref_height) ** alpha
    A = np.pi * (rotor_diameter / 2) ** 2
    eta_tot = Cp * eta_mech * eta_elec
    P_wind = 0.5 * rho * A * (v_hub ** 3) * eta_tot

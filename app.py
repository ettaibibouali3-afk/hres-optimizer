import streamlit as st
import numpy as np
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="HRES Optimizer", page_icon="⚡", layout="wide")

st.title("⚡ Hybrid Renewable Energy System Optimizer")
st.markdown("**Optimal sizing of off-grid PV-Wind-Battery systems for Morocco**")

# Sidebar
st.sidebar.header("System Parameters")
location_options = {
    "Ouarzazate (Desert)": (30.92, -6.90),
    "Dakhla (Coastal)": (23.72, -15.93),
    "Tangier (Mediterranean)": (35.78, -5.81),
    "Ifrane (Mountain)": (33.53, -5.11),
}
selected_location = st.sidebar.selectbox("Select Location", list(location_options.keys()))
lat, lon = location_options[selected_location]
st.sidebar.info(f"Coordinates: {lat}, {lon}")

load_kw = st.sidebar.slider("Load Demand (kW)", 1, 50, 5)
lpsp_target = st.sidebar.slider("Max LPSP (%)", 1, 20, 5) / 100
cost_pv = st.sidebar.number_input("PV Cost ($/kW)", value=800)
cost_wind = st.sidebar.number_input("Wind Cost ($/kW)", value=1200)
cost_batt = st.sidebar.number_input("Battery Cost ($/kWh)", value=300)

# Models
def pv_power(ghi, temp, P_rated):
    T_cell = temp + 25 * (ghi / 800)
    temp_factor = 1 + (-0.4 / 100) * (T_cell - 25)
    return np.clip(P_rated * (ghi / 1000) * temp_factor * 0.9, 0, P_rated)

def wind_power(ws, P_rated):
    v_hub = ws * (30 / 10) ** 0.14
    A = np.pi * 100
    P = 0.5 * 1.225 * A * (v_hub ** 3) * 0.361 / 1000
    P = np.where(v_hub < 3, 0, P)
    P = np.where(v_hub > 25, 0, P)
    return np.clip(P, 0, P_rated)

def simulate(ghi, ws, temp, Ppv, Pw, Bc, Pl):
    pv = pv_power(ghi, temp, Ppv)
    wind = wind_power(ws, Pw)
    gen = pv + wind
    n = len(ghi)
    soc = np.zeros(n)
    unmet = np.zeros(n)
    soc[0] = 0.5
    for t in range(n):
        net = gen[t] - Pl
        if net >= 0:
            soc_new = min(1.0, soc[t] + net * 0.95 / Bc)
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
    Eload = Pl * n
    lpsp = np.sum(unmet) / Eload
    return Epv, Ew, Eload, lpsp

def lcoe(Ppv, Pw, Bc, Eserved):
    capex = Ppv * cost_pv + Pw * cost_wind + Bc * cost_batt
    crf = 0.08 * 1.08**25 / (1.08**25 - 1)
    return (capex * crf + capex * 0.015) / Eserved, capex

def objective(x, ghi, ws, temp, Pl, lpsp_max):
    Ppv, Pw, Bc = x
    Epv, Ew, Eload, lpsp = simulate(ghi, ws, temp, Ppv, Pw, Bc, Pl)
    Eserved = Eload * (1 - lpsp)
    cost, _ = lcoe(Ppv, Pw, Bc, Eserved)
    if lpsp > lpsp_max:
        return cost + 1e6 * (lpsp - lpsp_max)
    return cost

def pso(ghi, ws, temp, Pl, lpsp_max, progress):
    np.random.seed(42)
    bounds = [(5, 100), (5, 100), (50, 500)]
    n_part, n_iter = 20, 50
    parts = np.array([[np.random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_part)])
    vels = np.zeros_like(parts)
    pbest = parts.copy()
    pbest_f = np.array([objective(p, ghi, ws, temp, Pl, lpsp_max) for p in parts])
    gbest = pbest[np.argmin(pbest_f)].copy()
    gbest_f = np.min(pbest_f)
    hist = [gbest_f]
    for it in range(n_iter):
        for i in range(n_part):
            r1, r2 = np.random.rand(3), np.random.rand(3)
            vels[i] = 0.7 * vels[i] + 1.5 * r1 * (pbest[i] - parts[i]) + 1.5 * r2 * (gbest - parts[i])
            parts[i] = np.clip(parts[i] + vels[i], [b[0] for b in bounds], [b[1] for b in bounds])
            f = objective(parts[i], ghi, ws, temp, Pl, lpsp_max)
            if f < pbest_f[i]:
                pbest[i], pbest_f[i] = parts[i].copy(), f
                if f < gbest_f:
                    gbest, gbest_f = parts[i].copy(), f
        hist.append(gbest_f)
        progress.progress((it + 1) / n_iter)
    return gbest, gbest_f, hist

@st.cache_data(ttl=3600)
def fetch_data(lat, lon):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {'lat': lat, 'lon': lon, 'outputformat': 'json', 'usehorizon': 1, 'startyear': 2005, 'endyear': 2023}
    r = requests.get(url, params=params, timeout=60)
    df = pd.DataFrame(r.json()['outputs']['tmy_hourly'])
    df = df.rename(columns={'G(h)': 'GHI', 'T2m': 'temp', 'WS10m': 'wind_speed'})
    df['wind_speed'] = df['wind_speed'].clip(lower=0)
    return df

# Main content
st.header("Click below to start optimization")

if st.button("🔄 Fetch Data and Optimize", type="primary"):
    with st.spinner("Fetching PVGIS data..."):
        df = fetch_data(lat, lon)
        st.success(f"Loaded {len(df)} hourly records")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Annual GHI", f"{df['GHI'].sum()/1000:.0f} kWh/m2")
    col2.metric("Mean Wind", f"{df['wind_speed'].mean():.1f} m/s")
    col3.metric("Mean Temp", f"{df['temp'].mean():.1f} C")
    
    st.subheader("Running PSO Optimization...")
    progress = st.progress(0)
    
    best, fitness, hist = pso(df['GHI'].values, df['wind_speed'].values, df['temp'].values, load_kw, lpsp_target, progress)
    
    st.success("Optimization complete!")
    
    st.subheader("Optimal System Sizing")
    c1, c2, c3 = st.columns(3)
    c1.metric("PV Capacity", f"{best[0]:.1f} kW")
    c2.metric("Wind Capacity", f"{best[1]:.1f} kW")
    c3.metric("Battery Capacity", f"{best[2]:.1f} kWh")
    
    Epv, Ew, Eload, lpsp = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values, best[0], best[1], best[2], load_kw)
    Eserved = Eload * (1 - lpsp)
    cost, capex = lcoe(best[0], best[1], best[2], Eserved)
    
    st.subheader("Economic Results")
    c4, c5, c6 = st.columns(3)
    c4.metric("CAPEX", f"${capex:,.0f}")
    c5.metric("LCOE", f"{cost*100:.2f} c/kWh")
    c6.metric("Reliability", f"{(1-lpsp)*100:.1f}%")
    
    st.subheader("Energy Mix")
    fig = go.Figure(data=[go.Pie(labels=['Solar', 'Wind'], values=[Epv, Ew], marker_colors=['#E85D24', '#3B8BD4'])])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Convergence")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(y=hist, mode='lines', line=dict(color='#1D9E75', width=2)))
    fig2.update_layout(xaxis_title="Iteration", yaxis_title="LCOE ($/kWh)", height=300)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.markdown("**HRES Optimizer** | IEEE Access Paper | Morocco 2025")

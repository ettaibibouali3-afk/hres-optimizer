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
    st.sidebar.info(f"Coordinates: {lat}°N, {lon}°W")

load_kw = st.sidebar.slider("Load Demand (kW)", min_value=1, max_value=50, value=5)
lpsp_target = st.sidebar.slider("Max LPSP (%)", min_value=1, max_value=20, value=5) / 100

st.sidebar.header("💰 Cost Parameters ($/unit)")
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
    P_wind = 0.5 * rho * A * (v_hub ** 3) * eta_tot / 1000
    P_wind = np.where(v_hub < v_cutin, 0, P_wind)
    P_wind = np.where(v_hub > v_cutout, 0, P_wind)
    return np.clip(P_wind, 0, P_rated)

def battery_model(P_gen, P_load, B_cap, SoC_init=0.5, SoC_min=0.2, SoC_max=1.0, eta_b=0.95):
    n_hours = len(P_gen)
    SoC = np.zeros(n_hours)
    P_unmet = np.zeros(n_hours)
    SoC[0] = SoC_init
    P_load_arr = np.full(n_hours, P_load) if np.isscalar(P_load) else P_load
    
    for t in range(n_hours):
        P_net = P_gen[t] - P_load_arr[t]
        if P_net >= 0:
            E_charge = P_net * eta_b
            E_room = (SoC_max - SoC[t]) * B_cap
            SoC_new = SoC[t] + min(E_charge, E_room) / B_cap
        else:
            E_needed = -P_net / eta_b
            E_available = (SoC[t] - SoC_min) * B_cap
            if E_needed <= E_available:
                SoC_new = SoC[t] - E_needed / B_cap
            else:
                P_unmet[t] = -P_net - E_available * eta_b
                SoC_new = SoC_min
        if t < n_hours - 1:
            SoC[t + 1] = SoC_new
    return SoC, P_unmet

def simulate_system(ghi, wind_speed, temp, P_pv, P_wind, B_cap, P_load):
    pv_out = pv_power(ghi, temp, P_pv)
    wind_out = wind_power(wind_speed, P_wind)
    total_gen = pv_out + wind_out
    SoC, P_unmet = battery_model(total_gen, P_load, B_cap)
    E_pv, E_wind = np.sum(pv_out), np.sum(wind_out)
    E_load = P_load * len(ghi)
    E_served = E_load - np.sum(P_unmet)
    lpsp = np.sum(P_unmet) / E_load if E_load > 0 else 0
    return {'E_pv': E_pv, 'E_wind': E_wind, 'E_load': E_load, 'E_served': E_served, 'LPSP': lpsp, 'SoC': SoC, 'pv_out': pv_out, 'wind_out': wind_out}

def calculate_lcoe(P_pv, P_wind, B_cap, E_served, cost_pv, cost_wind, cost_batt, lifetime=25, discount_rate=0.08):
    capex = P_pv * cost_pv + P_wind * cost_wind + B_cap * cost_batt
    opex = capex * 0.015
    CRF = (discount_rate * (1 + discount_rate)**lifetime) / ((1 + discount_rate)**lifetime - 1)
    lcoe = (capex * CRF + opex) / E_served if E_served > 0 else float('inf')
    return lcoe, capex

def objective_function(x, ghi, wind_speed, temp, P_load, lpsp_max, cost_pv, cost_wind, cost_batt):
    P_pv, P_wind, B_cap = x
    if P_pv < 0 or P_wind < 0 or B_cap < 0:
        return 1e9
    r = simulate_system(ghi, wind_speed, temp, P_pv, P_wind, B_cap, P_load)
    lcoe, _ = calculate_lcoe(P_pv, P_wind, B_cap, r['E_served'], cost_pv, cost_wind, cost_batt)
    if r['LPSP'] > lpsp_max:
        return lcoe + 1e6 * (r['LPSP'] - lpsp_max)
    return lcoe

def pso_optimize(ghi, wind_speed, temp, P_load, lpsp_max, cost_pv, cost_wind, cost_batt,
                 n_particles=20, max_iter=50, bounds=[(5,100), (5,100), (50,500)], progress_callback=None):
    np.random.seed(42)
    n_dim = 3
    particles = np.array([[np.random.uniform(bounds[d][0], bounds[d][1]) for d in range(n_dim)] for _ in range(n_particles)])
    velocities = np.array([[np.random.uniform(-(bounds[d][1]-bounds[d][0])*0.1, (bounds[d][1]-bounds[d][0])*0.1) for d in range(n_dim)] for _ in range(n_particles)])
    
    p_best = particles.copy()
    p_best_fitness = np.array([objective_function(p, ghi, wind_speed, temp, P_load, lpsp_max, cost_pv, cost_wind, cost_batt) for p in particles])
    g_best = p_best[np.argmin(p_best_fitness)].copy()
    g_best_fitness = np.min(p_best_fitness)
    history = [g_best_fitness]
    w, c1, c2 = 0.7, 1.5, 1.5
    
    for iteration in range(max_iter):
        for i in range(n_particles):
            r1, r2 = np.random.rand(n_dim), np.random.rand(n_dim)
            velocities[i] = w * velocities[i] + c1 * r1 * (p_best[i] - particles[i]) + c2 * r2 * (g_best - particles[i])
            particles[i] = np.clip(particles[i] + velocities[i], [b[0] for b in bounds], [b[1] for b in bounds])
            fitness = objective_function(particles[i], ghi, wind_speed, temp, P_load, lpsp_max, cost_pv, cost_wind, cost_batt)
            if fitness < p_best_fitness[i]:
                p_best[i], p_best_fitness[i] = particles[i].copy(), fitness
                if fitness < g_best_fitness:
                    g_best, g_best_fitness = particles[i].copy(), fitness
        history.append(g_best_fitness)
        if progress_callback:
            progress_callback((iteration + 1) / max_iter)
    return g_best, g_best_fitness, history

@st.cache_data(ttl=3600)
def fetch_pvgis_data(lat, lon):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {'lat': lat, 'lon': lon, 'outputformat': 'json', 'usehorizon': 1, 'startyear': 2005, 'endyear': 2023}
    response = requests.get(url, params=params, timeout=60)
    data = response.json()
    df = pd.DataFrame(data['outputs']['tmy_hourly'])
    df = df.rename(columns={'G(h)': 'GHI', 'T2m': 'temp', 'WS10m': 'wind_speed'})
    df['wind_speed'] = df['wind_speed'].clip(lower=0)
    return df

# ============================================================
# MAIN
# ============================================================
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📊 Resource Data")
    if st.button("🔄 Fetch Data & Optimize", type="primary"):
        with st.spinner("Fetching PVGIS data..."):
            try:
                df = fetch_pvgis_data(lat, lon)
                st.success(f"✓ Loaded {len(df)} hourly records")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Annual GHI", f"{df['GHI'].sum()/1000:.0f} kWh/m²")
                c2.metric("Mean Wind", f"{df['wind_speed'].mean():.1f} m/s")
                c3.metric("Mean Temp", f"{df['temp'].mean():.1f} °C")
                
                st.subheader("⚙️ Running PSO Optimization...")
                progress = st.progress(0)
                
                best, fitness, history = pso_optimize(
                    df['GHI'].values, df['wind_speed'].values, df['temp'].values,
                    load_kw, lpsp_target, cost_pv, cost_wind, cost_batt,
                    progress_callback=lambda p: progress.progress(p)
                )
                
                st.session_state['results'] = {'solution': best, 'fitness': fitness, 'history': history, 'df': df}
                st.success("✓ Optimization complete!")
            except Exception as e:
                st.error(f"Error: {e}")

with col2:
    st.header("📈 Results")
    if 'results' in st.session_state:
        r = st.session_state['results']
        sol, df = r['solution'], r['df']
        
        st.subheader("🎯 Optimal System Sizing")
        c1, c2, c3 = st.columns(3)
        c1.metric("☀️ PV", f"{sol[0]:.1f} kW")
        c2.metric("💨 Wind", f"{sol[1]:.1f} kW")
        c3.metric("🔋 Battery", f"{sol[2]:.1f} kWh")
        
        sim = simulate_system(df['GHI'].values, df['wind_speed'].values, df['temp'].values, sol[0], sol[1], sol[2], load_kw)
        lcoe, capex = calculate_lcoe(sol[0], sol[1], sol[2], sim['E_served'], cost_pv, cost_wind, cost_batt)
        
        st.subheader("💰 Economics")
        c4, c5, c6 = st.columns(3)
        c4.metric("CAPEX", f"${capex:,.0f}")
        c5.metric("LCOE", f"{lcoe*100:.2f} ¢/kWh")
        c6.metric("Reliability", f"{(1-sim['LPSP'])*100:.1f}%")
        
        st.subheader("⚡ Energy Mix")
        fig = go.Figure(data=[go.Pie(labels=['Solar', 'Wind'], values=[sim['E_pv'], sim['E_wind']], marker_colors=['#E85D24', '#3B8BD4'])])
        fig.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📉 Convergence")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(y=r['history'], mode='lines', line=dict(color='#1D9E75', width=2)))
        fig2.update_layout(xaxis_title="Iteration", yaxis_title="LCOE ($/kWh)", height=250, margin=dict(t=10, b=40, l=40, r=10))
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.markdown("**HRES Optimizer** | Developed for IEEE Access Paper | Morocco 2025")
```

Click **"Commit new file"**

---

### File 2: `requirements.txt`

Click **"Add file"** → **"Create new file"** → Name it `requirements.txt`

Paste this:
```
streamlit
numpy
pandas
requests
plotly

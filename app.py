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
    page_title="HRES Optimizer Morocco",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown('<p class="main-header">⚡ HRES Optimizer Morocco</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Optimal Sizing of Off-Grid Hybrid PV-Wind-Battery Systems</p>', unsafe_allow_html=True)

# ============================================================
# MOROCCO SITES DATA
# ============================================================
MOROCCO_SITES = {
    "Ouarzazate": {"lat": 30.92, "lon": -6.90, "climate": "Desert", "icon": "🏜️"},
    "Dakhla": {"lat": 23.72, "lon": -15.93, "climate": "Coastal", "icon": "🌊"},
    "Tangier": {"lat": 35.78, "lon": -5.81, "climate": "Mediterranean", "icon": "🌿"},
    "Ifrane": {"lat": 33.53, "lon": -5.11, "climate": "Mountain", "icon": "🏔️"},
    "Marrakech": {"lat": 31.63, "lon": -8.01, "climate": "Semi-arid", "icon": "🌴"},
    "Casablanca": {"lat": 33.57, "lon": -7.59, "climate": "Coastal", "icon": "🏙️"},
    "Fes": {"lat": 34.03, "lon": -5.00, "climate": "Continental", "icon": "🕌"},
    "Agadir": {"lat": 30.43, "lon": -9.60, "climate": "Semi-arid", "icon": "☀️"},
}

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("🎛️ Configuration")
    
    # Site Selection
    st.subheader("📍 Location")
    site_option = st.radio("Select site type:", ["Predefined Sites", "Custom Location"])
    
    if site_option == "Predefined Sites":
        selected_sites = st.multiselect(
            "Choose site(s):",
            list(MOROCCO_SITES.keys()),
            default=["Ouarzazate"]
        )
        if not selected_sites:
            selected_sites = ["Ouarzazate"]
    else:
        custom_lat = st.number_input("Latitude", value=31.63, min_value=20.0, max_value=36.0)
        custom_lon = st.number_input("Longitude", value=-8.01, min_value=-17.0, max_value=-1.0)
        selected_sites = ["Custom"]
        MOROCCO_SITES["Custom"] = {"lat": custom_lat, "lon": custom_lon, "climate": "Custom", "icon": "📍"}
    
    st.divider()
    
    # Load Profile
    st.subheader("⚡ Load Profile")
    load_type = st.radio("Load type:", ["Fixed Load", "Variable Load (Residential)"])
    
    if load_type == "Fixed Load":
        load_kw = st.slider("Constant load (kW)", 1, 50, 5)
    else:
        st.info("📊 Residential pattern: 1.5-7 kW (peak at 19:00)")
        load_kw = 3.6  # Average
    
    st.divider()
    
    # Optimization Settings
    st.subheader("⚙️ Optimization")
    algorithm = st.selectbox("Algorithm:", ["PSO", "GA", "GWO", "Compare All"])
    lpsp_target = st.slider("Max LPSP (%)", 1, 20, 5) / 100
    
    st.divider()
    
    # Cost Parameters
    st.subheader("💰 Cost Parameters ($/unit)")
    cost_pv = st.number_input("PV ($/kW)", value=600, step=50)
    cost_wind = st.number_input("Wind ($/kW)", value=1000, step=50)
    cost_batt = st.number_input("Battery ($/kWh)", value=250, step=25)
    
    st.divider()
    
    # Run Button
    run_optimization = st.button("🚀 Run Optimization", type="primary", use_container_width=True)

# ============================================================
# LOAD PROFILE
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

# ============================================================
# MODELS
# ============================================================
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

# ============================================================
# OPTIMIZATION ALGORITHMS
# ============================================================
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
        # Selection (tournament)
        new_pop = []
        for _ in range(pop_size):
            i, j = np.random.randint(0, pop_size, 2)
            winner = pop[i] if fitness[i] < fitness[j] else pop[j]
            new_pop.append(winner.copy())
        new_pop = np.array(new_pop)
        
        # Crossover
        for i in range(0, pop_size - 1, 2):
            if np.random.rand() < 0.8:
                alpha = np.random.rand(3)
                child1 = alpha * new_pop[i] + (1 - alpha) * new_pop[i + 1]
                child2 = (1 - alpha) * new_pop[i] + alpha * new_pop[i + 1]
                new_pop[i], new_pop[i + 1] = child1, child2
        
        # Mutation
        for i in range(pop_size):
            if np.random.rand() < 0.1:
                j = np.random.randint(0, 3)
                new_pop[i, j] = np.random.uniform(bounds[j][0], bounds[j][1])
        
        # Clip to bounds
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

# ============================================================
# DATA FETCHING
# ============================================================
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
    # Create tabs
    if len(selected_sites) > 1 or algorithm == "Compare All":
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Results", "📈 Comparison", "🗺️ Map", "📥 Export"])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Results", "📈 Analysis", "⚡ Dispatch", "📥 Export"])
    
    all_results = {}
    
    with tab1:
        for site_name in selected_sites:
            site_info = MOROCCO_SITES[site_name]
            
            st.subheader(f"{site_info['icon']} {site_name} ({site_info['climate']})")
            
            with st.spinner(f"Fetching data for {site_name}..."):
                df = fetch_data(site_info['lat'], site_info['lon'])
            
            # Display resource metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("☀️ Annual GHI", f"{df['GHI'].sum()/1000:.0f} kWh/m²")
            col2.metric("💨 Mean Wind", f"{df['wind_speed'].mean():.1f} m/s")
            col3.metric("🌡️ Mean Temp", f"{df['temp'].mean():.1f} °C")
            col4.metric("📍 Coordinates", f"{site_info['lat']:.2f}, {site_info['lon']:.2f}")
            
            # Create load profile
            load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
            
            # Run optimization
            ghi = df['GHI'].values
            ws = df['wind_speed'].values
            temp = df['temp'].values
            
            if algorithm == "Compare All":
                st.write("Running all algorithms...")
                progress = st.progress(0)
                
                results_pso = pso_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.33)
                results_ga = ga_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(0.66)
                results_gwo = gwo_optimize(ghi, ws, temp, load_profile, lpsp_target, cost_pv, cost_wind, cost_batt)
                progress.progress(1.0)
                
                # Find best
                all_algo_results = [results_pso, results_ga, results_gwo]
                best_result = min(all_algo_results, key=lambda x: x['fitness'])
                
                # Show comparison
                st.write("**Algorithm Comparison:**")
                algo_df = pd.DataFrame({
                    'Algorithm': ['PSO', 'GA', 'GWO'],
                    'LCOE (¢/kWh)': [r['fitness']*100 for r in all_algo_results],
                    'PV (kW)': [r['solution'][0] for r in all_algo_results],
                    'Wind (kW)': [r['solution'][1] for r in all_algo_results],
                    'Battery (kWh)': [r['solution'][2] for r in all_algo_results]
                })
                st.dataframe(algo_df, use_container_width=True)
                
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
            
            # Get solution
            sol = result['solution']
            sim = simulate(ghi, ws, temp, sol[0], sol[1], sol[2], load_profile)
            lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim['Eserved'], cost_pv, cost_wind, cost_batt)
            
            st.success(f"✓ Optimization complete using {result['algorithm']}!")
            
            # Results
            st.write("**Optimal System Sizing:**")
            col1, col2, col3 = st.columns(3)
            col1.metric("☀️ PV Capacity", f"{sol[0]:.1f} kW")
            col2.metric("💨 Wind Capacity", f"{sol[1]:.1f} kW")
            col3.metric("🔋 Battery", f"{sol[2]:.1f} kWh")
            
            st.write("**Economic Results:**")
            col4, col5, col6 = st.columns(3)
            col4.metric("💵 CAPEX", f"${capex:,.0f}")
            col5.metric("⚡ LCOE", f"{lcoe_val*100:.2f} ¢/kWh")
            col6.metric("✅ Reliability", f"{sim['reliability']:.1f}%")
            
            # Charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # Energy mix pie chart
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['Solar', 'Wind'],
                    values=[sim['Epv'], sim['Ew']],
                    marker_colors=['#F59E0B', '#3B82F6'],
                    hole=0.4
                )])
                fig_pie.update_layout(
                    title="Energy Mix",
                    height=300,
                    margin=dict(t=40, b=20, l=20, r=20)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                # Convergence curve
                fig_conv = go.Figure()
                fig_conv.add_trace(go.Scatter(
                    y=[h*100 for h in result['history']],
                    mode='lines',
                    line=dict(color='#10B981', width=2),
                    name=result['algorithm']
                ))
                fig_conv.update_layout(
                    title="Convergence Curve",
                    xaxis_title="Iteration",
                    yaxis_title="LCOE (¢/kWh)",
                    height=300,
                    margin=dict(t=40, b=40, l=40, r=20)
                )
                st.plotly_chart(fig_conv, use_container_width=True)
            
            st.divider()
    
    # Tab 2: Comparison or Analysis
    with tab2:
        if len(selected_sites) > 1:
            st.subheader("📈 Multi-Site Comparison")
            
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
                        'GHI (kWh/m²)': int(df['GHI'].sum()/1000),
                        'Wind (m/s)': round(df['wind_speed'].mean(), 1),
                        'PV (kW)': round(sol[0], 1),
                        'Wind (kW)': round(sol[1], 1),
                        'Battery (kWh)': round(sol[2], 1),
                        'CAPEX ($)': int(capex),
                        'LCOE (¢/kWh)': round(lcoe_val*100, 2)
                    })
            
            if comparison_data:
                df_comp = pd.DataFrame(comparison_data)
                st.dataframe(df_comp, use_container_width=True)
                
                # Bar chart comparison
                fig_comp = make_subplots(rows=1, cols=2, subplot_titles=('LCOE Comparison', 'CAPEX Comparison'))
                
                fig_comp.add_trace(
                    go.Bar(x=df_comp['Site'], y=df_comp['LCOE (¢/kWh)'], marker_color='#3B82F6', name='LCOE'),
                    row=1, col=1
                )
                fig_comp.add_trace(
                    go.Bar(x=df_comp['Site'], y=df_comp['CAPEX ($)'], marker_color='#10B981', name='CAPEX'),
                    row=1, col=2
                )
                
                fig_comp.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.subheader("📈 Detailed Analysis")
            
            if selected_sites[0] in all_results:
                site_name = selected_sites[0]
                df = all_results[site_name]['df']
                result = all_results[site_name]['best']
                sol = result['solution']
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values,
                               sol[0], sol[1], sol[2], load_profile)
                
                # Monthly analysis
                df['month'] = pd.to_datetime(df['time(UTC)'], format='%Y%m%d:%H%M').dt.month
                monthly_ghi = df.groupby('month')['GHI'].sum() / 1000
                monthly_wind = df.groupby('month')['wind_speed'].mean()
                
                fig_monthly = make_subplots(rows=1, cols=2, subplot_titles=('Monthly GHI', 'Monthly Wind Speed'))
                
                fig_monthly.add_trace(
                    go.Bar(x=monthly_ghi.index, y=monthly_ghi.values, marker_color='#F59E0B', name='GHI'),
                    row=1, col=1
                )
                fig_monthly.add_trace(
                    go.Bar(x=monthly_wind.index, y=monthly_wind.values, marker_color='#3B82F6', name='Wind'),
                    row=1, col=2
                )
                
                fig_monthly.update_layout(height=350, showlegend=False)
                fig_monthly.update_xaxes(title_text="Month", row=1, col=1)
                fig_monthly.update_xaxes(title_text="Month", row=1, col=2)
                fig_monthly.update_yaxes(title_text="kWh/m²", row=1, col=1)
                fig_monthly.update_yaxes(title_text="m/s", row=1, col=2)
                st.plotly_chart(fig_monthly, use_container_width=True)
    
    # Tab 3: Map or Dispatch
    with tab3:
        if len(selected_sites) > 1:
            st.subheader("🗺️ Site Locations")
            
            map_data = []
            for site_name in selected_sites:
                if site_name in MOROCCO_SITES:
                    site = MOROCCO_SITES[site_name]
                    map_data.append({
                        'lat': site['lat'],
                        'lon': site['lon'],
                        'site': site_name
                    })
            
            if map_data:
                df_map = pd.DataFrame(map_data)
                st.map(df_map, latitude='lat', longitude='lon', size=50)
        else:
            st.subheader("⚡ Hourly Dispatch (Sample Week)")
            
            if selected_sites[0] in all_results:
                site_name = selected_sites[0]
                df = all_results[site_name]['df']
                result = all_results[site_name]['best']
                sol = result['solution']
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values,
                               sol[0], sol[1], sol[2], load_profile)
                
                # Show first week (168 hours)
                hours = list(range(168))
                
                fig_dispatch = go.Figure()
                fig_dispatch.add_trace(go.Scatter(x=hours, y=sim['pv'][:168], name='PV', fill='tozeroy', line=dict(color='#F59E0B')))
                fig_dispatch.add_trace(go.Scatter(x=hours, y=sim['wind'][:168], name='Wind', fill='tozeroy', line=dict(color='#3B82F6')))
                fig_dispatch.add_trace(go.Scatter(x=hours, y=load_profile[:168], name='Load', line=dict(color='#EF4444', width=2, dash='dash')))
                
                fig_dispatch.update_layout(
                    title="Power Generation vs Load (First Week)",
                    xaxis_title="Hour",
                    yaxis_title="Power (kW)",
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig_dispatch, use_container_width=True)
                
                # SoC chart
                fig_soc = go.Figure()
                fig_soc.add_trace(go.Scatter(x=hours, y=sim['soc'][:168]*100, name='SoC', line=dict(color='#10B981', width=2)))
                fig_soc.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Min SoC (20%)")
                fig_soc.update_layout(
                    title="Battery State of Charge",
                    xaxis_title="Hour",
                    yaxis_title="SoC (%)",
                    height=300
                )
                st.plotly_chart(fig_soc, use_container_width=True)
    
    # Tab 4: Export
    with tab4:
        st.subheader("📥 Export Results")
        
        export_data = []
        for site_name in selected_sites:
            if site_name in all_results:
                result = all_results[site_name]['best']
                df = all_results[site_name]['df']
                sol = result['solution']
                load_profile = create_load_profile(load_type, load_kw if load_type == "Fixed Load" else 5)
                sim = simulate(df['GHI'].values, df['wind_speed'].values, df['temp'].values,
                               sol[0], sol[1], sol[2], load_profile)
                lcoe_val, capex = lcoe(sol[0], sol[1], sol[2], sim['Eserved'], cost_pv, cost_wind, cost_batt)
                
                export_data.append({
                    'Site': site_name,
                    'Algorithm': result['algorithm'],
                    'Load Type': load_type,
                    'PV (kW)': round(sol[0], 2),
                    'Wind (kW)': round(sol[1], 2),
                    'Battery (kWh)': round(sol[2], 2),
                    'CAPEX ($)': round(capex, 2),
                    'LCOE ($/kWh)': round(lcoe_val, 4),
                    'LCOE (¢/kWh)': round(lcoe_val*100, 2),
                    'Reliability (%)': round(sim['reliability'], 2),
                    'Annual PV (MWh)': round(sim['Epv']/1000, 2),
                    'Annual Wind (MWh)': round(sim['Ew']/1000, 2),
                    'Annual Load (MWh)': round(sim['Eload']/1000, 2)
                })
        
        if export_data:
            df_export = pd.DataFrame(export_data)
            st.dataframe(df_export, use_container_width=True)
            
            # Download button
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name="hres_optimization_results.csv",
                mime="text/csv",
                use_container_width=True
            )

else:
    # Welcome screen
    st.info("👈 Configure parameters in the sidebar and click **Run Optimization** to start.")
    
    # Show Morocco map with all sites
    st.subheader("🗺️ Available Sites in Morocco")
    
    map_data = []
    for site_name, site_info in MOROCCO_SITES.items():
        if site_name != "Custom":
            map_data.append({
                'lat': site_info['lat'],
                'lon': site_info['lon'],
                'site': f"{site_info['icon']} {site_name}"
            })
    
    df_map = pd.DataFrame(map_data)
    st.map(df_map, latitude='lat', longitude='lon', size=100)
    
    # Site info table
    st.subheader("📊 Site Information")
    site_info_data = []
    for site_name, info in MOROCCO_SITES.items():
        if site_name != "Custom":
            site_info_data.append({
                'Site': f"{info['icon']} {site_name}",
                'Climate': info['climate'],
                'Latitude': info['lat'],
                'Longitude': info['lon']
            })
    
    st.dataframe(pd.DataFrame(site_info_data), use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**🔬 Research Tool**")
    st.caption("IEEE Access Paper")
with col2:
    st.markdown("**📍 Morocco Focus**")
    st.caption("4 Climate Zones")
with col3:
    st.markdown("**⚡ Algorithms**")
    st.caption("PSO, GA, GWO")

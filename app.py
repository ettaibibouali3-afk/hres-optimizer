"""
HRES Optimizer — Streamlit Application
======================================

Off-grid PV–wind–battery–diesel hybrid renewable energy system sizing for
any location worldwide. Runs all five metaheuristic algorithms (PSO, GWO,
APO, APO-PSO, GJO) and recommends the configuration with lowest TNPC
satisfying user-defined LPSP and REP constraints.

This app is the user interface for the optimization framework described in
the accompanying paper. All simulation, economic, and optimization functions
are imported from core.py (which preserves the validated notebook code).
"""

import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
from utils.site_runtime import prepare_site, reset_load_profile, detect_climate_zone


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="HRES Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================
def _init_state():
    defaults = {
        "site_ready": False,
        "current_site": None,
        "results_ready": False,
        "all_runs": None,
        "best_run": None,
        "best_algo": None,
        "best_seed": None,
        "ems_state": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# ============================================================
# CSS (compact dark theme)
# ============================================================
st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #0f172a 0%, #0c4a6e 100%);
        padding: 1.5rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;
        border: 1px solid rgba(56, 189, 248, 0.2);
    }
    .hero h1 {
        background: linear-gradient(135deg, #38bdf8, #34d399);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; margin: 0;
    }
    .hero p { color: #cbd5e1; margin: 0.4rem 0 0 0; }
    .winner-card {
        background: linear-gradient(145deg, #1e3a5f, #0c4a6e);
        border: 2px solid #38bdf8; border-radius: 16px;
        padding: 1.5rem; margin: 1rem 0;
    }
    .winner-card h3 { color: #38bdf8; margin-top: 0; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <div class="hero">
        <h1>⚡ HRES Optimizer</h1>
        <p>Off-grid PV–wind–battery–diesel sizing for any location.
        All five metaheuristic algorithms run automatically; the best
        configuration is selected by lowest Total Net Present Cost.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR — Configuration
# ============================================================
with st.sidebar:
    st.header("⚙️ Configuration")

    # ── Location ──────────────────────────────────────────
    st.subheader("📍 Location")
    location_mode = st.radio(
        "Mode",
        ["Use a paper study site", "Custom location"],
        label_visibility="collapsed",
    )

    if location_mode == "Use a paper study site":
        site_name = st.selectbox(
            "Study site",
            list(core.STUDY_SITES.keys()),
        )
        site_info = core.STUDY_SITES[site_name]
        lat = site_info["lat"]
        lon = site_info["lon"]
        region = site_info["region"]
        climate = site_info["climate"]
        diesel_default = site_info["fuel_price_USD_per_L"]
        ir_nom_default = site_info["ir_nom"]
        fr_default = site_info["fr"]
    else:
        site_name = st.text_input("Site name", value="Custom Location")
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input(
                "Latitude", -60.0, 70.0, 25.0, 0.01, format="%.4f"
            )
        with col2:
            lon = st.number_input(
                "Longitude", -180.0, 180.0, 0.0, 0.01, format="%.4f"
            )
        region = st.text_input("Region (label only)", value="Custom")
        climate = detect_climate_zone(lat, lon)
        st.caption(f"Climate zone (auto): **{climate}**")
        diesel_default = 1.50
        ir_nom_default = 0.05
        fr_default = 0.03

    # ── Constraints ───────────────────────────────────────
    st.subheader("🎯 Constraints")
    LPSP_target = st.slider(
        "LPSP* (max loss-of-power probability)",
        0.00, 0.10, 0.02, 0.01, format="%.2f",
        help="Maximum allowed unmet-load fraction. 0.02 = 2% of annual demand.",
    )
    REP_target = st.slider(
        "REP* (min renewable energy share)",
        0.30, 0.95, 0.70, 0.05, format="%.2f",
        help="Minimum fraction of supplied energy from renewables.",
    )

    # ── Economics ─────────────────────────────────────────
    st.subheader("💵 Economics")
    fuel_price = st.number_input(
        "Diesel price (USD/L)",
        0.10, 5.00, float(diesel_default), 0.01, format="%.2f",
    )
    ir_nom_pct = st.number_input(
        "Nominal interest rate (%)",
        0.0, 30.0, float(ir_nom_default) * 100, 0.05, format="%.2f",
        help="Central bank policy rate.",
    )
    fr_pct = st.number_input(
        "Inflation rate (%)",
        0.0, 50.0, float(fr_default) * 100, 0.05, format="%.3f",
        help="2024 annual CPI from IMF WEO.",
    )

    ir_nom = ir_nom_pct / 100
    fr = fr_pct / 100
    ir_raw = (ir_nom - fr) / (1 + fr)
    ir_used = max(ir_raw, core.IR_FLOOR)
    floored = ir_raw < core.IR_FLOOR

    st.markdown("**Derived:**")
    st.caption(
        f"Real rate (raw): **{ir_raw*100:.2f}%** → "
        f"used: **{ir_used*100:.2f}%**"
        + (" *(floored at 1%)*" if floored else "")
    )

    # ── Load ──────────────────────────────────────────────
    st.subheader("⚡ Load")
    avg_load = st.number_input(
        "Average load (kW)",
        1.0, 500.0, 36.0, 1.0,
        help="Annual average power demand.",
    )

    # ── Algorithm settings ────────────────────────────────
    st.subheader("🔬 Algorithm Settings")
    n_seeds = st.slider("Seeds per algorithm", 1, 10, 3,
                         help="More seeds = more reliable result, longer runtime.")
    pop_size = st.slider("Population size", 10, 50, 20)
    n_iter = st.slider("Iterations", 20, 200, 50)

    total_runs = 5 * n_seeds
    est_time_min = total_runs * (pop_size * n_iter) / 30000
    st.caption(
        f"5 algorithms × {n_seeds} seeds = **{total_runs} runs** "
        f"(~{est_time_min:.1f} min)"
    )

    st.divider()
    run_button = st.button("🚀 Optimize", type="primary", use_container_width=True)


# ============================================================
# MAIN — handle Run button
# ============================================================
if run_button:
    st.session_state.results_ready = False
    st.session_state.all_runs = None

    # ── Step 1: Prepare site ──────────────────────────────
    with st.status("🌐 Preparing site...", expanded=True) as status:
        try:
            st.write(f"Fetching PVGIS TMY data for {site_name} ({lat:.3f}, {lon:.3f})...")
            prepare_site(
                site_name=site_name,
                lat=lat, lon=lon,
                fuel_price_USD_per_L=fuel_price,
                ir_nom=ir_nom, fr=fr,
                avg_load_kW=avg_load,
                region=region,
                climate=climate,
            )
            # Always refresh load profile for current avg_load
            reset_load_profile(site_name, avg_load, lat)
            st.write("✅ Weather data loaded")
            st.write("✅ PV unit profile precomputed")
            st.write("✅ Load profile generated")
            st.session_state.site_ready = True
            st.session_state.current_site = site_name
            status.update(label="✅ Site ready", state="complete")
        except Exception as e:
            status.update(label=f"❌ Error: {e}", state="error")
            st.stop()

    # ── Step 2: Run all 5 algorithms ──────────────────────
    # Each algorithm uses a different keyword for population size
    ALGORITHMS = [
        ("PSO",     core.pso_optimize,    "n_particles"),
        ("GWO",     core.gwo_optimize,    "n_wolves"),
        ("APO",     core.apo_optimize,    "n_puffins"),
        ("APO-PSO", core.apopso_optimize, "n_agents"),
        ("GJO",     core.gjo_optimize,    "n_jackals"),
    ]

    seeds = [42, 123, 456, 789, 2026, 31415, 27182, 101, 2024, 999][:n_seeds]

    progress = st.progress(0)
    status_text = st.empty()
    live_table_box = st.empty()

    all_runs = []
    best_fitness = np.inf
    best_run = None
    best_algo = None
    best_seed = None

    total = len(ALGORITHMS) * len(seeds)
    counter = 0
    t_start = time.time()

    for algo_name, algo_fn, pop_kw in ALGORITHMS:
        for seed in seeds:
            counter += 1
            elapsed = time.time() - t_start
            eta = (elapsed / counter) * (total - counter) if counter > 0 else 0
            status_text.markdown(
                f"**{algo_name}** — seed {seed} "
                f"({counter}/{total}) — ETA {eta:.0f}s"
            )

            t0 = time.time()
            try:
                kwargs = {
                    "site_name": site_name,
                    "LPSP_target": LPSP_target,
                    "REP_target": REP_target,
                    "seed": seed,
                    "n_iter": n_iter,
                    "verbose": False,
                    pop_kw: pop_size,
                }
                result = algo_fn(**kwargs)
                runtime = time.time() - t0
                m = result["metrics"]
                row = {
                    "algorithm": algo_name,
                    "seed": seed,
                    "TNPC": float(m["TNPC"]),
                    "LCOE": float(m["LCOE"]),
                    "LPSP": float(m["LPSP"]),
                    "REP": float(m["REP"]),
                    "DSF": float(m["DSF"]),
                    "CDRA": float(m["CDRA"]),
                    "N_pv": int(m["N_pv"]),
                    "N_wt": int(m["N_wt"]),
                    "N_bat": int(m["N_bat"]),
                    "N_dg": int(m["N_dg"]),
                    "feasible": bool(m["feasible"]),
                    "runtime_s": round(runtime, 2),
                }
                all_runs.append(row)

                # Track best feasible result by TNPC
                if m["feasible"] and m["TNPC"] < best_fitness:
                    best_fitness = m["TNPC"]
                    best_run = result
                    best_algo = algo_name
                    best_seed = seed

            except Exception as e:
                all_runs.append({
                    "algorithm": algo_name, "seed": seed,
                    "TNPC": np.nan, "feasible": False,
                    "error": str(e)[:120], "runtime_s": np.nan,
                })

            progress.progress(counter / total)

            # Live table (update every 5 runs)
            if counter % 5 == 0 or counter == total:
                df_live = pd.DataFrame(all_runs)
                if not df_live.empty and "TNPC" in df_live.columns:
                    summary = (
                        df_live.dropna(subset=["TNPC"])
                        .groupby("algorithm")["TNPC"]
                        .agg(["mean", "min", "std"])
                        .round(0)
                    )
                    live_table_box.dataframe(summary, use_container_width=True)

    progress.empty()
    status_text.empty()
    live_table_box.empty()

    if best_run is None:
        st.error(
            "⚠ No feasible configuration found. Try relaxing LPSP* or REP* "
            "constraints, or increasing population / iterations."
        )
        st.stop()

    st.session_state.all_runs = all_runs
    st.session_state.best_run = best_run
    st.session_state.best_algo = best_algo
    st.session_state.best_seed = best_seed
    st.session_state.results_ready = True
    st.session_state.ems_state = best_run["metrics"]["ems"]


# ============================================================
# RESULTS DISPLAY
# ============================================================
if st.session_state.results_ready:
    best_run = st.session_state.best_run
    best_algo = st.session_state.best_algo
    best_seed = st.session_state.best_seed
    all_runs = st.session_state.all_runs
    m = best_run["metrics"]
    site_name = st.session_state.current_site

    # ── Winner panel ──────────────────────────────────────
    st.markdown(
        f"""
        <div class="winner-card">
            <h3>🏆 Recommended configuration — {best_algo} (seed {best_seed})</h3>
            <p style="color:#cbd5e1;margin:0;">
                Selected as the lowest feasible TNPC across all 5 algorithms ×
                {len(set(r['seed'] for r in all_runs))} seeds.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PV panels", f"{m['N_pv']}", f"{m['N_pv']*0.2:.1f} kWp")
    c2.metric("Wind turbines", f"{m['N_wt']}", f"{m['N_wt']*100:.0f} kW")
    c3.metric("Battery units", f"{m['N_bat']}", f"{m['E_bat_kWh']:.0f} kWh")
    c4.metric("DG units", f"{m['N_dg']}", f"{m['N_dg']*core.pdg_r:.0f} kW")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TNPC", f"${m['TNPC']:,.0f}")
    c2.metric("LCOE", f"${m['LCOE']:.4f}/kWh")
    c3.metric("Annual CO₂ avoided", f"{m['CDRA']:.1f} t")
    c4.metric("Diesel saved", f"{m['fuel_saved_L']:,.0f} L/yr")

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "LPSP", f"{m['LPSP']*100:.2f}%",
        "✓ feasible" if m["LPSP"] <= LPSP_target else "✗",
    )
    c2.metric(
        "REP", f"{m['REP']*100:.1f}%",
        "✓ feasible" if m["REP"] >= REP_target else "✗",
    )
    c3.metric("DSF (hours met)", f"{m['DSF']*100:.2f}%")

    st.divider()

    # ── Algorithm comparison table ────────────────────────
    st.subheader("Algorithm comparison")

    df = pd.DataFrame(all_runs).dropna(subset=["TNPC"])
    summary = (
        df.groupby("algorithm")
        .agg(
            best_TNPC=("TNPC", "min"),
            mean_TNPC=("TNPC", "mean"),
            std_TNPC=("TNPC", "std"),
            mean_runtime=("runtime_s", "mean"),
            feasible_count=("feasible", "sum"),
        )
        .round({"best_TNPC": 0, "mean_TNPC": 0, "std_TNPC": 0, "mean_runtime": 1})
        .sort_values("best_TNPC")
    )
    summary.columns = [
        "Best TNPC ($)", "Mean TNPC ($)", "Std Dev ($)",
        "Avg runtime (s)", f"Feasible / {n_seeds}",
    ]
    st.dataframe(summary, use_container_width=True)

    st.caption(
        f"**Winner:** {best_algo} achieved the lowest feasible TNPC of "
        f"${m['TNPC']:,.0f}. Configurations with LPSP > {LPSP_target*100:.0f}% "
        f"or REP < {REP_target*100:.0f}% are excluded from the recommendation."
    )

    # ── Charts ────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("TNPC breakdown")
        bd = m["TNPC_breakdown"]
        labels = ["PV array", "Wind turbines", "Battery",
                  "Diesel generator", "Converter"]
        values = [bd["TNPC_pv"], bd["TNPC_wt"], bd["TNPC_bat"],
                  bd["TNPC_dg"], bd["TNPC_cnv"]]
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.45,
            marker_colors=["#f9c74f", "#90be6d", "#4cc9f0",
                           "#f94144", "#adb5bd"],
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=350,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Annual energy balance")
        ems = m["ems"]
        fig = go.Figure(go.Bar(
            x=["PV", "Wind", "Diesel", "Dump", "Unmet"],
            y=[ems["E_pv_annual"]/1000, ems["E_wt_annual"]/1000,
               ems["E_dg_annual"]/1000, ems["E_dump_annual"]/1000,
               ems["LPS_total"]/1000],
            marker_color=["#f9c74f", "#90be6d", "#f94144",
                          "#adb5bd", "#e63946"],
            text=[f"{v/1000:.1f}" for v in [ems["E_pv_annual"], ems["E_wt_annual"],
                  ems["E_dg_annual"], ems["E_dump_annual"], ems["LPS_total"]]],
            textposition="outside",
        ))
        fig.update_layout(
            yaxis_title="MWh/yr",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=350,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Sample week dispatch ──────────────────────────────
    st.subheader("Sample week — power dispatch")
    week_start = st.slider(
        "Week starting at hour", 0, 8760 - 168, 0, 168,
        format="%d (day %d)",
    )
    h0, h1 = week_start, week_start + 168
    hours = np.arange(168)
    ems = m["ems"]
    load_profile = core.LOAD_PROFILES[site_name]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours, y=ems["P_pv_dc"][h0:h1],
        name="PV (DC)", fill="tozeroy",
        line=dict(color="#f9c74f", width=0),
        fillcolor="rgba(249,199,79,0.5)",
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=ems["P_wt_dc"][h0:h1],
        name="Wind (DC)", fill="tozeroy",
        line=dict(color="#90be6d", width=0),
        fillcolor="rgba(144,190,109,0.5)",
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=ems["P_dg"][h0:h1],
        name="Diesel (AC)", fill="tozeroy",
        line=dict(color="#f94144", width=0),
        fillcolor="rgba(249,65,68,0.5)",
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=load_profile[h0:h1],
        name="Load (AC)",
        line=dict(color="#ffffff", width=2, dash="dash"),
    ))
    fig.update_layout(
        xaxis_title="Hour of week",
        yaxis_title="Power (kW)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=400,
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=30, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Downloads ─────────────────────────────────────────
    st.subheader("Export results")
    c1, c2 = st.columns(2)

    with c1:
        df_best = pd.DataFrame([{
            "site": site_name,
            "lat": lat, "lon": lon,
            "algorithm": best_algo,
            "seed": best_seed,
            "N_pv": m["N_pv"], "N_wt": m["N_wt"],
            "N_bat": m["N_bat"], "N_dg": m["N_dg"],
            "E_bat_kWh": m["E_bat_kWh"],
            "TNPC_USD": m["TNPC"],
            "LCOE_USD_kWh": m["LCOE"],
            "LPSP_pct": round(m["LPSP"]*100, 3),
            "REP_pct": round(m["REP"]*100, 1),
            "DSF_pct": round(m["DSF"]*100, 1),
            "CDRA_tCO2_yr": round(m["CDRA"], 2),
            "fuel_saved_L_yr": round(m["fuel_saved_L"], 0),
            "CRF": m["CRF"],
            "fuel_price_USD_L": fuel_price,
            "ir_nom_pct": ir_nom_pct,
            "fr_pct": fr_pct,
            "LPSP_target": LPSP_target,
            "REP_target": REP_target,
        }])
        st.download_button(
            "⬇ Recommended configuration (CSV)",
            df_best.to_csv(index=False),
            f"hres_optimal_{site_name.replace(' ', '_').replace(',', '')}.csv",
            "text/csv", use_container_width=True,
        )

    with c2:
        df_all = pd.DataFrame(all_runs)
        st.download_button(
            "⬇ All algorithm runs (CSV)",
            df_all.to_csv(index=False),
            f"hres_all_runs_{site_name.replace(' ', '_').replace(',', '')}.csv",
            "text/csv", use_container_width=True,
        )

else:
    # ── Welcome screen ────────────────────────────────────
    st.info(
        "👈 Configure your site and constraints in the sidebar, "
        "then click **Optimize** to run all five metaheuristic algorithms."
    )

    st.markdown(
        """
        ### What this platform does

        - **Any location worldwide** — choose one of the 8 paper study sites
          or enter custom coordinates (PVGIS TMY data is fetched automatically)
        - **All five algorithms** — PSO, GWO, APO, APO-PSO, and GJO run
          in parallel with multiple seeds
        - **Best-of selection** — the recommended configuration is the
          single run achieving the lowest feasible TNPC across all algorithms
        - **Site-specific economics** — diesel price, nominal interest rate,
          and inflation per Table 9; 1% real-rate floor applied; 4% escalation
        - **Climate-aware load profile** — automatic hemisphere correction
          for seasonal demand pattern
        """
    )

    st.markdown("### Available paper study sites")
    df_sites = pd.DataFrame([
        {"Site": k, "Lat": v["lat"], "Lon": v["lon"],
         "Climate": v["climate"], "Region": v["region"],
         "Diesel (USD/L)": v["fuel_price_USD_per_L"]}
        for k, v in core.STUDY_SITES.items()
    ])
    st.dataframe(df_sites, use_container_width=True, hide_index=True)


# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "HRES Optimizer · companion platform for the multi-site, multi-algorithm "
    "off-grid hybrid renewable energy system sizing study. "
    "PVGIS data: © European Commission Joint Research Centre. "
    "Inflation rates: IMF World Economic Outlook Oct 2024. "
    "Diesel prices: GlobalPetrolPrices.com."
)

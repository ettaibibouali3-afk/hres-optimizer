
# ============================================================
# SHIM: defaults removed by static cleaning (originally globals().get())
# These are defined here to ensure they're available at function-definition time
# ============================================================
_ETA_CNV_DEFAULT = 0.95
_ETA_BC_DEFAULT  = 0.97
_ETA_BD_DEFAULT  = 0.97
_DOD_DEFAULT     = 0.90
_SIGMA_DEFAULT   = 1e-5
_PDG_R_DEFAULT   = 10.0

# -*- coding: utf-8 -*-



# Cell 1: Imports & Setup

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import brentq
import time
import warnings




# Cell 2: Study Sites Definition
# ============================================================
# 8 Global South Sites - Diverse climates and resources
# Economic parameters:
#   fuel_price_USD_per_L : diesel price in USD/L
#   ir_nom               : nominal interest rate, decimal
#   fr                   : inflation rate, decimal
# ============================================================

STUDY_SITES = {
    "Dakhla, Morocco": {
        "country": "Morocco",
        "lat": 23.72, "lon": -15.93,
        "region": "North Africa",
        "climate": "Coastal Desert",
        "description": "Excellent wind + solar",
        "fuel_price_USD_per_L": 1.57,
        "ir_nom": 0.0225,
        "fr": 0.01720,
    },

    "Cairo, Egypt": {
        "country": "Egypt",
        "lat": 30.04, "lon": 31.24,
        "region": "North Africa",
        "climate": "Hot Desert",
        "description": "High solar, moderate wind",
        "fuel_price_USD_per_L": 0.38,
        "ir_nom": 0.1900,
        "fr": 0.33302,
    },

    "Nairobi, Kenya": {
        "country": "Kenya",
        "lat": -1.29, "lon": 36.82,
        "region": "Sub-Saharan Africa",
        "climate": "Tropical Highland",
        "description": "Moderate solar, low wind",
        "fuel_price_USD_per_L": 1.52,
        "ir_nom": 0.0875,
        "fr": 0.05118,
    },

    "Dubai, UAE": {
        "country": "United Arab Emirates",
        "lat": 25.20, "lon": 55.27,
        "region": "Middle East",
        "climate": "Hot Desert",
        "description": "Very high solar, moderate wind",
        "fuel_price_USD_per_L": 1.28,
        "ir_nom": 0.0365,
        "fr": 0.02300,
    },

    "Karachi, Pakistan": {
        "country": "Pakistan",
        "lat": 24.86, "lon": 67.01,
        "region": "South Asia",
        "climate": "Arid Coastal",
        "description": "Good solar + coastal wind",
        "fuel_price_USD_per_L": 1.43,
        "ir_nom": 0.1150,
        "fr": 0.23411,
    },

    "Bangkok, Thailand": {
        "country": "Thailand",
        "lat": 13.76, "lon": 100.50,
        "region": "Southeast Asia",
        "climate": "Tropical",
        "description": "Moderate solar, low wind",
        "fuel_price_USD_per_L": 1.23,
        "ir_nom": 0.0150,
        "fr": 0.00535,
    },

    "Santiago, Chile": {
        "country": "Chile",
        "lat": -33.45, "lon": -70.67,
        "region": "Latin America",
        "climate": "Mediterranean",
        "description": "Good solar, very low wind",
        "fuel_price_USD_per_L": 1.57,
        "ir_nom": 0.0475,
        "fr": 0.03898,
    },

    "Suva, Fiji": {
        "country": "Fiji",
        "lat": -18.14, "lon": 178.44,
        "region": "Oceania",
        "climate": "Tropical Island",
        "description": "Moderate solar, good wind",
        "fuel_price_USD_per_L": 1.74,
        "ir_nom": 0.0025,
        "fr": 0.05200,
    },
}

# Display Table 1: Site Characteristics



# Regional distribution
regions = {}



# Display economic parameters for verification



# Cell 3: Fetch PVGIS Weather Data for All Sites
# ============================================================
# Source: European Commission Joint Research Centre
# Data: Typical Meteorological Year (TMY) - Hourly resolution
# ============================================================

def fetch_pvgis_data(lat, lon, site_name="Unknown"):
    """Fetch TMY data from PVGIS API"""
    url = "https://re.jrc.ec.europa.eu/api/v5_3/tmy"
    params = {
        "lat": lat, "lon": lon,
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
        df["GHI"] = df["GHI"].clip(lower=0)
        df["wind_speed"] = df["wind_speed"].clip(lower=0)

        if len(df) != 8760:
            print(f"⚠️ {site_name}: {len(df)} hours (expected 8760)")
            return None
        return df

    except Exception as e:
        print(f"❌ {site_name}: {e}")
        return None


def calculate_metrics(df):
    """Calculate resource metrics from weather data"""
    return {
        "GHI_kWh_m2_yr": round(df["GHI"].sum() / 1000, 1),
        "temp_mean_C": round(df["temp"].mean(), 1),
        "wind_mean_ms": round(df["wind_speed"].mean(), 2),
        "wind_hours_above_3ms": int((df["wind_speed"] >= 3).sum())
    }


# Fetch data for all sites

all_site_data = {}
all_metrics = []





# Create metrics DataFrame


# Display resource summary (TABLE 1 extended)



# Key statistics


# Cell 4: Wind Turbine Model
# ============================================================
# Equations (1)-(3), Mokhtara et al. (2021)
#
# Step 1: Hub-height wind speed extrapolation — Eq.(X)
#   V_hub = V_ref * (H_hub / H_ref)^alpha
#   V_ref  = wind speed at reference height (PVGIS = 10m)
#   H_hub  = turbine hub height (m)
#   H_ref  = reference height = 10m
#   alpha  = wind shear exponent = 1/7 = 0.143 (open terrain)
#
# Step 2: Wind power output — Eqs.(1)-(3)
#   P = 0                              if V < Vcutin or V > Vcutout
#   P = (V^3 - Vcutin^3) /
#       (Vrated^3 - Vcutin^3) * Pr    if Vcutin ≤ V ≤ Vrated
#   P = Pr                             if Vrated < V < Vcutout
#
# Turbine: 100 kW class
# Hub height: 50m (typical for 100kW class turbine)
# Reference height: 10m (PVGIS default)
# ============================================================

import numpy as np

def wind_speed_hub(V_ref, H_hub=50.0, H_ref=10.0, alpha=1/7):
    """
    Hub-height wind speed extrapolation.
    Power law profile — standard wind energy practice.

    Parameters
    ----------
    V_ref  : array — wind speed at reference height (m/s)
    H_hub  : float — turbine hub height (m), default 50m
    H_ref  : float — reference height (m), default 10m
    alpha  : float — wind shear exponent, default 1/7 = 0.143

    Returns
    -------
    V_hub : array — wind speed at hub height (m/s)
    """
    V_ref = np.asarray(V_ref, dtype=float)
    return V_ref * (H_hub / H_ref) ** alpha


def wind_power(V, Pr, Vcutin, Vrated, Vcutout):
    """
    Wind turbine power output — Eqs.(1)-(3), Mokhtara et al. (2021)

    Parameters
    ----------
    V       : array — wind speed at hub height (m/s)
    Pr      : float — rated power (kW)
    Vcutin  : float — cut-in speed (m/s)
    Vrated  : float — rated speed (m/s)
    Vcutout : float — cut-out speed (m/s)

    Returns
    -------
    P : array — power output (kW)
    """
    V = np.asarray(V, dtype=float)
    P = np.zeros_like(V)

    # Region 2: cut-in to rated — cubic interpolation Eq.(2)
    m2 = (V >= Vcutin) & (V <= Vrated)
    P[m2] = ((V[m2]**3 - Vcutin**3) /
              (Vrated**3 - Vcutin**3)) * Pr

    # Region 3: rated to cut-out — full power Eq.(3)
    m3 = (V > Vrated) & (V < Vcutout)
    P[m3] = Pr

    return P


# ── Turbine parameters ────────────────────────────────────────
WT_PARAMS = {
    "Pr":      100.0,    # rated power (kW)
    "Vcutin":  2.5,      # cut-in speed (m/s)
    "Vrated":  11.0,     # rated speed (m/s)
    "Vcutout": 20.0,     # cut-out speed (m/s)
    "H_hub":   50.0,     # hub height (m)
    "H_ref":   10.0,     # reference height (m) — PVGIS default
    "alpha":   1/7,      # wind shear exponent — open terrain
}

# ── Verification ──────────────────────────────────────────────

# Test hub-height correction




# Cell 4b: Solar PV Model — Hybrid One-Diode Approach
# ============================================================
# Model: Single-diode equivalent circuit with full I0(T)
# Ref:   Villalva, M.G., Gazoli, J.R., & Filho, E.R. (2009).
#        Comprehensive approach to modeling and simulation of
#        photovoltaic arrays. IEEE Trans. Power Electron.,
#        24(5), 1198–1208.
#        https://doi.org/10.1109/TPEL.2009.2013862
#
# Strategy: HYBRID (precompute + scale)
#   Step 1: Solve one-diode model ONCE per site → P_unit(t)
#   Step 2: During optimization:
#           P_pv(t) = P_unit(t) × N_pv  — O(8760), no solver
#
# One-diode equations:
#   I  = Iph - I0*(exp((V+I*Rs)/(n*Vt)) - 1) - (V+I*Rs)/Rsh
#   Iph = (Isc_stc + Ki*(T-Tref)) * G/Gref
#   I0 = I0_stc * (T/Tref)^3 * exp[q*Eg/(n*k) * (1/Tref - 1/T)]
#   I0_stc = Isc_stc / (exp(Voc_stc / Vt_stc) - 1)
#   Vt = n*k*T/q   (thermal voltage)
#
# Cell temperature:
#   T_cell = T_amb + (NOCT - 20) / 800 * G
#
# Output cap (FIX H1):
#   P_unit ≤ 1.05 × Pmpp_stc to account for inverter clipping
#   and prevent unphysical values at low cell temperature.
# ============================================================

import numpy as np
from scipy.optimize import brentq
from scipy.constants import elementary_charge as Q_E
from scipy.constants import Boltzmann as K_B

# ── PV module parameters ──────────────────────────────────────
PV_MODULE = {
    "Pmpp_stc":  200.0,    # W
    "Vmpp_stc":  26.3,     # V
    "Impp_stc":  7.61,     # A
    "Voc_stc":   32.9,     # V
    "Isc_stc":   8.21,     # A
    "Ki":        0.0032,   # A/°C
    "Kv":       -0.1230,   # V/°C
    "n":         1.3,      # ideality factor
    "Rs":        0.221,    # series resistance (Ω)
    "Rsh":       415.0,    # shunt resistance (Ω)
    "Eg":        1.121,    # bandgap energy (eV)
    "G_ref":     1000.0,   # reference irradiance (W/m²)
    "T_ref":     25.0,     # reference cell temperature (°C)
    "NOCT":      45.0,     # Nominal Operating Cell Temperature (°C)
    "pr_panel":  468.0,    # $/panel — Alsaqqar & Abuelrub (2026) Table 2
    "ppvr":      0.200,    # rated power (kW)
    "P_cap_factor": 1.05,  # FIX H1: cap output at 1.05 × Pmpp_stc
}


def solve_one_diode_mpp(G, T_c, params=PV_MODULE):
    """
    Solve one-diode model at MPP for given (G, T_cell).
    Returns peak power in W (capped at 1.05 × Pmpp_stc).
    """
    if G < 1.0:
        return 0.0

    n      = params["n"]
    Rs     = params["Rs"]
    Rsh    = params["Rsh"]
    Ki     = params["Ki"]
    Kv     = params["Kv"]
    Isc0   = params["Isc_stc"]
    Voc0   = params["Voc_stc"]
    G0     = params["G_ref"]
    T0     = params["T_ref"]
    Eg     = params["Eg"]
    Pmpp0  = params["Pmpp_stc"]
    P_cap  = params["P_cap_factor"] * Pmpp0   # FIX H1

    T_k    = T_c + 273.15
    T0_k   = T0  + 273.15
    dT     = T_c - T0

    Vt     = n * K_B * T_k / Q_E
    Vt_stc = n * K_B * T0_k / Q_E

    Iph    = (Isc0 + Ki * dT) * (G / G0)
    I0_stc = Isc0 / (np.exp(Voc0 / Vt_stc) - 1)

    # Full temperature-dependent I0 — Villalva et al. (2009)
    I0 = (I0_stc
          * (T_k / T0_k)**3
          * np.exp((Q_E * Eg / (n * K_B))
                   * (1.0/T0_k - 1.0/T_k)))

    Voc_t = max(Voc0 + Kv * dT, 0.1)

    def iv_equation(I, V):
        return (Iph
                - I0 * (np.exp((V + I*Rs) / Vt) - 1)
                - (V + I*Rs) / Rsh
                - I)

    V_scan  = np.linspace(0, Voc_t * 0.99, 100)
    P_best  = 0.0
    n_fail  = 0

    for V in V_scan:
        try:
            I_sol = brentq(iv_equation, 0, Iph + 0.1,
                           args=(V,), xtol=1e-6)
            P = V * I_sol
            if P > P_best:
                P_best = P
        except ValueError:
            # brentq sign-error: no root in interval — skip silently
            n_fail += 1
            continue

    # FIX H1: cap at 1.05 × Pmpp_stc (inverter clipping)
    return min(P_best, P_cap)


def precompute_pv_unit(site_df, params=PV_MODULE):
    """
    Precompute hourly power output of 1 PV panel (kW).
    Uses site_df["temp"] for ambient temperature.
    """
    G_arr = site_df["GHI"].values.astype(float)
    T_arr = (site_df["temp"].values.astype(float)
             if "temp" in site_df.columns
             else np.full(len(site_df), 25.0))

    NOCT   = params["NOCT"]
    P_unit = np.zeros(len(G_arr))

    for t in range(len(G_arr)):
        G   = G_arr[t]
        T_c = T_arr[t] + (NOCT - 20.0) / 800.0 * G
        P_unit[t] = solve_one_diode_mpp(G, T_c, params) / 1000.0

    return P_unit


def pv_power_output(P_unit_arr, N_pv):
    """
    Scale precomputed unit profile by number of panels.
    O(8760) — no iterative solver inside optimization loop.
    """
    return np.asarray(P_unit_arr, dtype=float) * int(N_pv)


# ── Precompute for all sites ─────────────────────────────────

PV_UNIT_PROFILES = {}




# ── Verification ──────────────────────────────────────────────



# Cell 4c: Diesel Generator Fuel Model
# ============================================================
# Ref: Alsaqqar & Abuelrub (2026), Eq.(9), Section 2.2.3
#      Original fuel curve — Skarstein & Uhlen (1989),
#      Wind Engineering, vol. 13, no. 2, pp. 72-87.
#      Adopted by Dufo-López & Bernal-Agustín (2008),
#      Renewable Energy, 33(12), 2559–2572.
#
# Fuel consumption equation — Eq.(9):
#   F_dg(t) = α_dg * N_dg * pdg_r + β_dg * P_dg(t)   [L/h]
#
#   α_dg : idle/no-load coefficient — 0.024 L/kW
#   β_dg : load-dependent coefficient — 0.08145 L/kWh
#
# Decomposition:
#   - α_dg * Pr  → fuel consumed simply by being ON (idle losses)
#   - β_dg * P_dg → fuel proportional to delivered power
#
# DG ON/OFF logic:
#   P_DG <= 1e-6 → DG OFF → q = 0 (no fuel consumed)
#   P_DG >  1e-6 → DG ON  → apply Eq.(9)
# ============================================================

# ── Reference fuel coefficients (Alsaqqar & Abuelrub 2026) ───
ALPHA_DG = 0.024     # L/kW   — idle coefficient   — Eq.(9)
BETA_DG  = 0.08145   # L/kWh  — load coefficient   — Eq.(9)


def dg_fuel_consumption(P_DG, Pr_total):
    """
    Diesel fuel consumption — Eq.(9), Alsaqqar & Abuelrub (2026).
    Original: Skarstein & Uhlen (1989).

        F_dg = α_dg * Pr_total + β_dg * P_DG    [L/h]

    Parameters
    ----------
    P_DG     : float — actual DG output at time t (kW)
    Pr_total : float — total rated DG power (kW) = N_dg * pdg_r
                       pdg_r = 10.0 kW/unit (defined in Cell 5)

    Returns
    -------
    q : float — fuel consumption (L/h)
    """
    if P_DG <= 1e-6:
        return 0.0  # DG is OFF — no fuel consumed
    return ALPHA_DG * Pr_total + BETA_DG * P_DG


# ── Verification ──────────────────────────────────────────────

# Test cases (Pr_total = 10 kW = 1 unit × 10 kW/unit)

# Sanity check vs reference paper expected values
# At P=5 kW, Pr=10 kW: q = 0.024×10 + 0.08145×5 = 0.24 + 0.41 = 0.6473 L/h


# Cell 4d: Converter Model
# Eq.(8) — Mokhtara et al. (2021), Section 2.2.4

def converter_output(P_input, eta_cnv):
    """
    Eq.(8) — Mokhtara et al. (2021), Section 2.2.4:
    η_cnv = P_output / P_input
    → P_output = η_cnv * P_input
    η_cnv = 0.95  (Table 3)
    P_input  : input power  (kW)
    P_output : output power (kW)

    P_input <= 0 → converter OFF → no output
    """
    if P_input <= 0:
        return 0.0
    return eta_cnv * P_input

eta_cnv = 0.95   # Mokhtara et al. (2021), Table 3

# Verification

# Cell 4e: Battery Storage Model (Li-ion)
# ============================================================
# Eqs. (9)-(11) — Mokhtara et al. (2021), Section 2.2.5
#   (energy-balance equations, not Mokhtara's lead-acid params)
#
# Chemistry: Lithium-ion (LiFePO4 / NMC commercial modules)
# Reference:
#   IRENA (2023). "Innovation Outlook: Renewable Mini-grids."
#   Hesse, H.C. et al. (2017). Energies, 10(12), 2107.
#       (Li-ion roundtrip 92–96%)
#   LG RESU 5 kWh datasheet — η_RT = 95%, DOD = 95%
#
# Parameters (FIX C3):
#   η_BC = η_BD = 0.97     → roundtrip 0.97² ≈ 0.94
#   DOD  = 0.90            (Li-ion deep-cycle capability)
#   σ    = 1e-5 /hour      (≈0.7%/month — physical Li-ion value)
#   Lifetime: 10 yr        (calendar life, ≥4000 cycles)
#   Cost  : $300/kWh       (IRENA 2023)
# ============================================================

# ── Battery parameters (Li-ion) ──────────────────────────────
eta_BC = 0.97   # charge efficiency      — IRENA 2023, Hesse 2017
eta_BD = 0.97   # discharge efficiency   — IRENA 2023, Hesse 2017
sigma  = 1e-5   # self-discharge per hour ≈ 0.7%/month — Hesse 2017
DOD    = 0.90   # depth of discharge — Li-ion deep-cycle


def battery_discharge(Eb_t, Ei_t, Eg_t,
                      eta_cnv, eta_BD, sigma, Eb_min):
    """
    Eq.(9), Mokhtara et al. (2021):
      Eb(t+1) = Eb(t)*(1-σ) - [(Ei/eta_cnv - Eg) / eta_BD]
    Discharge mode: Ei/eta_cnv > Eg.
    """
    deficit = Ei_t / eta_cnv - Eg_t
    if deficit <= 0:
        return Eb_t  # safety: no deficit → unchanged
    Eb_next = Eb_t * (1 - sigma) - deficit / eta_BD
    return max(Eb_next, Eb_min)


def battery_charge(Eb_t, Ei_t, Eg_t,
                   eta_cnv, eta_BC, sigma, Eb_max):
    """
    Eq.(10), Mokhtara et al. (2021):
      Eb(t+1) = Eb(t)*(1-σ) + (Eg - Ei/eta_cnv) * eta_BC
    Charge mode: Eg > Ei/eta_cnv.
    """
    surplus = Eg_t - Ei_t / eta_cnv
    if surplus <= 0:
        return Eb_t  # safety: no surplus → unchanged
    Eb_next = Eb_t * (1 - sigma) + surplus * eta_BC
    return min(Eb_next, Eb_max)


def battery_soc_limits(Eb_max):
    """Eq.(11), Mokhtara et al. (2021):  Eb_min = (1 - DOD) * Eb_max"""
    Eb_min = (1 - DOD) * Eb_max
    return Eb_min, Eb_max


# ── Verification ──────────────────────────────────────────────

Eb_max = 10.0


# Charge — surplus exists
# Expected: 5*(1-1e-5) + (3 - 1/0.95)*0.97
#         ≈ 4.99995 + 1.9264*0.97 ≈ 6.8685

# Charge — no surplus (safety)

# Discharge — deficit exists
# Expected: 5*(1-1e-5) - (3/0.95 - 1)/0.97
#         ≈ 4.99995 - 2.1579/0.97 ≈ 2.7757

# Discharge — no deficit (safety)


# Cell 5: Economic Model and TNPC Calculation
# ============================================================
# Site-specific economic parameters are read from STUDY_SITES:
#   fuel_price_USD_per_L
#   ir_nom
#   fr
#
# Real interest rate:
#   ir_raw = (ir_nom - fr) / (1 + fr)
#
# A minimum real interest rate floor of 1% is applied (standard for project appraisal):
#   ir_used = max(ir_raw, 0.01)
#
# CRF:
#   CRF = ir_used*(1+ir_used)^N / ((1+ir_used)^N - 1)
#
# Escalation: all recurring costs (O&M, replacement, fuel) use a uniform long‑term
# escalation rate er = 4%, not the one‑year inflation rate.
# ============================================================

import numpy as np

# ── Economic settings ────────────────────────────────────────

er = 0.04          # long‑term escalation rate for O&M, replacement, fuel
N_proj = 20        # project lifetime, years
IR_FLOOR = 0.01    # minimum real interest rate (1% floor)


# ── Financial factor functions ───────────────────────────────

def capital_recovery_factor(ir, N):
    """Capital recovery factor. Handles ir=0 by returning 1/N."""
    if abs(ir) < 1e-9:
        return 1.0 / N
    return (ir * (1 + ir)**N) / ((1 + ir)**N - 1)


def npv_om(er, ir, N):
    """O&M escalation NPV factor. Costs escalate at er, discounted at ir."""
    return sum(((1 + er) / (1 + ir))**n for n in range(1, N + 1))


def npv_repl(escalation_rate, ir, years):
    """
    Replacement and fuel NPV factor.
    Costs escalate at `escalation_rate` (long‑term rate, e.g., 0.04),
    discounted at ir.
    """
    return sum(((1 + escalation_rate) / (1 + ir))**n for n in years)


def repl_years(lifetime, N):
    """Replacement years strictly within the project lifetime."""
    return list(range(lifetime, N, lifetime))


def get_economic_factors(site_name):
    """
    Return site-specific economic factors for TNPC and LCOE.

    Required keys inside STUDY_SITES[site_name]:
        country
        fuel_price_USD_per_L
        ir_nom
        fr
    """
    site_info = STUDY_SITES[site_name]

    ir_nom = site_info["ir_nom"]
    fr = site_info["fr"]
    FP_dg_site = site_info["fuel_price_USD_per_L"]

    # Fisher real interest rate
    ir_raw = (ir_nom - fr) / (1 + fr)

    # Minimum real interest rate floor (1%)
    ir_used = max(ir_raw, IR_FLOOR)

    # Capital recovery factor
    CRF_site = capital_recovery_factor(ir_used, N_proj)

    # NPV factors – all use long‑term escalation rate er (4%), not fr
    F_om_site = npv_om(er, ir_used, N_proj)
    F_dg_repl_site = npv_repl(er, ir_used, repl_years(10, N_proj))
    F_bat_repl_site = npv_repl(er, ir_used, repl_years(10, N_proj))
    F_fuel_site = npv_repl(er, ir_used, list(range(1, N_proj + 1)))

    # Converter replacement factor, year 10, using er
    cnv_repl_factor_site = ((1 + er) / (1 + ir_used))**10

    return {
        "country": site_info["country"],
        "FP_dg": FP_dg_site,
        "ir_nom": ir_nom,
        "fr": fr,
        "ir_raw": ir_raw,
        "ir_used": ir_used,
        "CRF": CRF_site,
        "F_om": F_om_site,
        "F_dg_repl": F_dg_repl_site,
        "F_bat_repl": F_bat_repl_site,
        "F_fuel": F_fuel_site,
        "cnv_repl_factor": cnv_repl_factor_site,
    }


# ── Component cost parameters ─────────────────────────────────

# PV — Alsaqqar & Abuelrub (2026), Table 2
pr_pv = 468.0                 # USD/panel
om_pv = 0.02 * pr_pv          # 2% CAPEX/year, USD/panel/year

# Wind turbine — IRENA (2023), small-scale onshore wind assumption
pr_wt = 1500.0                # USD/kW
om_wt = 50.0                  # USD/kW/year
Pr_wt = 100.0                 # kW per turbine

# Battery — Li-ion stationary storage assumption
pr_bat = 300.0                # USD/kWh
om_bat = 10.0                 # USD/kWh/year
r_bat = 250.0                 # USD/kWh replacement

# Diesel generator — Alsaqqar & Abuelrub (2026), Table 2
pr_dg = 550.0                 # USD/unit
pdg_r = 10.0                  # kW rated per diesel generator unit
R_dg = 550.0                  # USD/unit replacement
om_dg = 0.08                  # USD/kWh, DG O&M coefficient

# Diesel fuel coefficients — imported from Cell 4c
# (Ensure these are defined before running this cell)

# Converter / central inverter
pr_cnv = 100.0                # USD/kW
om_cnv = 0.01 * pr_cnv        # 1% CAPEX/year = 1 USD/kW/year


# ── TNPC per component ────────────────────────────────────────

def TNPC_pv(N_pv, econ):
    """
    PV array TNPC.
    No replacement is considered over the 20-year project lifetime.
    """
    I = pr_pv * N_pv
    OM = om_pv * N_pv * econ["F_om"]
    return I + OM


def TNPC_wt(N_wt, econ):
    """
    Wind turbine TNPC.
    No replacement is considered over the 20-year project lifetime.
    """
    P_total = N_wt * Pr_wt
    I = pr_wt * P_total
    OM = om_wt * P_total * econ["F_om"]
    return I + OM


def TNPC_bat(E_bat_kWh, econ):
    """
    Battery TNPC.
    Battery lifetime = 10 years, so one replacement is considered at year 10.
    """
    I = pr_bat * E_bat_kWh
    R = r_bat * E_bat_kWh * econ["F_bat_repl"]
    OM = om_bat * E_bat_kWh * econ["F_om"]
    return I + R + OM


def TNPC_dg(N_dg, P_dg_arr, econ):
    """
    Diesel generator TNPC.

    Includes:
        capital cost
        O&M cost
        replacement cost at year 10
        fuel cost NPV using site-specific diesel price
    """
    P_dg = np.maximum(np.asarray(P_dg_arr, dtype=float), 0.0)
    Pr_total = N_dg * pdg_r

    # Fuel consumption
    on_mask = P_dg > 1e-6

    if Pr_total > 0 and on_mask.any():
        F_dg_t = np.where(
            on_mask,
            ALPHA_DG * Pr_total + BETA_DG * P_dg,
            0.0
        )
    else:
        F_dg_t = np.zeros_like(P_dg)

    FC_annual = F_dg_t.sum()                 # L/year
    FC_year = econ["FP_dg"] * FC_annual      # USD/year

    # Cost components
    I = pr_dg * N_dg

    if pdg_r > 0:
        OM = om_dg * np.sum(P_dg / pdg_r) * econ["F_om"]
    else:
        OM = 0.0

    R = R_dg * N_dg * econ["F_dg_repl"]
    FC_npv = FC_year * econ["F_fuel"]

    return I + OM + R + FC_npv, FC_annual


def TNPC_cnv(P_cnv_kW, econ):
    """
    Converter / central inverter TNPC.
    Converter lifetime = 10 years, so one replacement is considered at year 10.
    """
    I = pr_cnv * P_cnv_kW
    R = pr_cnv * P_cnv_kW * econ["cnv_repl_factor"]
    OM = om_cnv * P_cnv_kW * econ["F_om"]
    return I + R + OM


def compute_TNPC(site_name, N_pv, N_wt, E_bat_kWh, N_dg, P_cnv_kW, P_dg_arr):
    """
    Total Net Present Cost with site-specific economic parameters.

    TNPC = TNPC_pv + TNPC_wt + TNPC_bat + TNPC_dg + TNPC_cnv
    """
    econ = get_economic_factors(site_name)

    pv_ = TNPC_pv(N_pv, econ)
    wt_ = TNPC_wt(N_wt, econ)
    bat_ = TNPC_bat(E_bat_kWh, econ)
    dg_, FC_annual = TNPC_dg(N_dg, P_dg_arr, econ)
    cnv_ = TNPC_cnv(P_cnv_kW, econ)

    total = pv_ + wt_ + bat_ + dg_ + cnv_

    return {
        "TNPC_pv": round(pv_, 2),
        "TNPC_wt": round(wt_, 2),
        "TNPC_bat": round(bat_, 2),
        "TNPC_dg": round(dg_, 2),
        "TNPC_cnv": round(cnv_, 2),
        "TNPC_total": round(total, 2),
        "FC_annual_L": round(FC_annual, 1),

        # Economic parameters used in this evaluation
        "FP_dg": round(econ["FP_dg"], 3),
        "ir_nom": round(econ["ir_nom"], 6),
        "fr": round(econ["fr"], 6),
        "ir_raw": round(econ["ir_raw"], 6),
        "ir_used": round(econ["ir_used"], 6),
        "CRF": round(econ["CRF"], 6),
    }


def compute_LCOE(TNPC_total, E_load_annual_kWh, CRF):
    """
    LCOE = TAC / annual useful load demand.
    TAC = CRF × TNPC
    """
    TAC = CRF * TNPC_total
    return TAC / E_load_annual_kWh if E_load_annual_kWh > 0 else 0.0


# ── Verification: site-specific economic parameters ──────────






# ── Verification: TNPC test case for each site ───────────────









# ── DG fuel sanity check ──────────────────────────────────────


# Expected:
# Pr_total = 5 × 10 = 50 kW
# P_dg = 5 kW
# q = ALPHA_DG × 50 + BETA_DG × 5
# q = 0.024 × 50 + 0.08145 × 5 = 1.60725 L/h
# annual = 1.60725 × 8760 = 14,079.51 L/year

expected_fuel = (ALPHA_DG * 50.0 + BETA_DG * 5.0) * 8760





# Cell 6: Load Profile — 8760-hour synthetic load array
# ============================================================
# 36 kW average demand, applied to all 8 sites
# with HEMISPHERE-CORRECTED seasonal phase (FIX M2):
#
#   Northern Hemisphere : peak in June (cooling-driven)
#   Southern Hemisphere : peak in December (cooling-driven)
#   Equatorial          : reduced amplitude (minimal seasonality)
#
# Justification:
#   "A uniform 36 kW average load is applied across all sites
#    to isolate the effect of renewable resource variability
#    on optimal HRES sizing. The seasonal phase is reversed
#    for Southern Hemisphere sites to reflect physically
#    consistent cooling demand timing, ensuring no artificial
#    coincidence between solar peak and demand peak."
#
# Daily pattern (typical commercial / community load):
#   - Base 45% night, morning peak 7–9h, evening peak 18–22h
#   - ±5% Gaussian noise
#
# Reference: Mokhtara et al. (2021); Bhandari et al. (2014);
#            Diab et al. (2020) — synthetic load conventions.
# ============================================================

import numpy as np


# ── Hemisphere classification (latitude-based) ───────────────
def site_hemisphere(lat, equatorial_band=10.0):
    """
    Return seasonal phase tag from latitude:
      'N' if lat >  +equatorial_band → Northern Hemisphere
      'S' if lat <  -equatorial_band → Southern Hemisphere
      'E' otherwise                  → Equatorial (no swing)
    """
    if lat >  equatorial_band: return "N"
    if lat < -equatorial_band: return "S"
    return "E"


def generate_load_profile(avg_load_kW=36.0,
                           hemisphere="N",
                           seasonal_amp=0.15,
                           equatorial_amp=0.05,
                           seed=42):
    """
    Generate synthetic 8760-h load profile with hemisphere-corrected
    seasonal phase.

    Parameters
    ----------
    avg_load_kW    : float — target annual average load (kW)
    hemisphere     : 'N', 'S', or 'E' (equatorial)
    seasonal_amp   : float — seasonal swing amplitude for N/S
    equatorial_amp : float — reduced amplitude for equatorial sites
    seed           : int   — RNG seed for noise reproducibility

    Returns
    -------
    P_load : np.ndarray (8760,) — hourly load (kW)
    """
    np.random.seed(seed)
    hours     = np.arange(8760)
    h_of_day  = hours % 24
    day_of_yr = hours // 24

    # ── Daily pattern (24 h) ─────────────────────────────────
    daily = np.zeros(24)
    daily[0:7]   = 0.45   # night
    daily[7:9]   = 0.85   # morning peak
    daily[9:12]  = 0.75   # mid-morning
    daily[12:14] = 0.70   # lunch dip
    daily[14:17] = 0.75   # afternoon
    daily[17:18] = 0.85   # pre-evening ramp
    daily[18:22] = 1.00   # evening peak
    daily[22:24] = 0.55   # late night
    P_daily = daily[h_of_day]

    # ── Seasonal phase (FIX M2) ──────────────────────────────
    # sin(2π(d − d_peak_offset)/365) peaks at d = d_peak
    # Northern: peak at d ≈ 172 (Jun 21) → offset 80
    # Southern: peak at d ≈ 355 (Dec 21) → offset 263 (= 80 + 183)
    if hemisphere == "N":
        amp    = seasonal_amp
        offset = 80
    elif hemisphere == "S":
        amp    = seasonal_amp
        offset = 263                    # Northern offset + 183 days
    else:  # 'E' equatorial
        amp    = equatorial_amp         # reduced swing
        offset = 80                     # arbitrary — small effect

    seasonal = 1.0 + amp * np.sin(
        2 * np.pi * (day_of_yr - offset) / 365)

    # ── Noise ±5% ────────────────────────────────────────────
    noise = 1.0 + 0.05 * np.random.randn(8760)
    noise = np.clip(noise, 0.90, 1.10)

    # ── Compose, scale, clip, rescale ────────────────────────
    P_raw  = P_daily * seasonal * noise
    P_load = P_raw * (avg_load_kW / P_raw.mean())

    P_min  = 0.30 * avg_load_kW
    P_max  = 1.80 * avg_load_kW
    P_load = np.clip(P_load, P_min, P_max)

    # Rescale to maintain target average after clipping
    P_load = P_load * (avg_load_kW / P_load.mean())

    return P_load


# ── Generate per-site profiles ────────────────────────────────
AVG_LOAD_KW = 36.0

LOAD_PROFILES = {}
LOAD_HEMISPHERES = {}



# ── Verification ──────────────────────────────────────────────



    # Find day of seasonal peak (smooth via 24h rolling mean)



# Sanity check: peak month


# Cell 7: Energy Management System (EMS)
# ============================================================
# 4-scenario dispatch logic — Section 2.6, Mokhtara et al. (2021)
#
# Scenario 1: DC renewable surplus → charges battery (DC bus)
# Scenario 2: DC surplus > battery capacity → dump load (AC bus)
# Scenario 3: DC renewables insufficient → battery discharges
# Scenario 4: DC renewables + battery insufficient → diesel ON
#
# Bus architecture — Fig. 1 (DC-bus EMS):
#   PV  → DC/DC converter → DC bus
#   WT  → AC/DC converter → DC bus
#   Bat ↔ Bidirectional DC/DC converter ↔ DC bus
#   DC bus → Central Inverter (η_cnv) → AC bus → Load
#   DG  → AC bus directly (no converter)
#
# Energy balance convention:
#   All generation and battery operations on DC bus.
#   AC load referred to DC bus as P_load / η_cnv.
#   η_cnv applied only at DC→AC inverter stage.
#   Energy reporting in AC-equivalent kWh for LCOE/REP consistency.
#
# Notes:
#   - Initial SOC: E_b(0) = 0.5 * E_bat_max  (Section 3.3, Eq.18)
#   - sigma   = 1e-5/h   (Li-ion self-discharge — Cell 4e, Hesse 2017)
#   - eta_BC  = eta_BD = 0.97 (Li-ion — Cell 4e, IRENA 2023)
#   - DOD     = 0.90     (Li-ion deep-cycle — Cell 4e)
#   - eta_cnv = 0.95     (central DC/AC inverter — Cell 4d, Mokhtara 2021)
#   - Battery balance uses DC quantities; η_BC, η_BD cover DC/DC
#     interface + electrochemical losses — no double-count with η_cnv.
#   - DG connects directly to AC bus — not subject to η_cnv.
#   - No DG minimum loading (system-level simplification —
#     Mokhtara et al. 2021; Diab et al. 2020).
#   - Dump load on AC bus: DC surplus converted via η_cnv before dump.
# ============================================================

import numpy as np

# ── Resolve global parameters at function-definition time ────


def run_EMS(P_pv_arr, P_wt_arr, P_load_arr,
            E_bat_max, N_dg,
            eta_cnv = _ETA_CNV_DEFAULT,
            eta_BC  = _ETA_BC_DEFAULT,
            eta_BD  = _ETA_BD_DEFAULT,
            DOD     = _DOD_DEFAULT,
            sigma   = _SIGMA_DEFAULT,
            pdg_r   = _PDG_R_DEFAULT):
    """
    Hourly DC-bus EMS simulation — 8760 time steps (Δt = 1h).

    DC-bus convention (Fig. 1, Section 3.3):
        P_ren_dc(t)  = P_pv(t) + P_wt(t)          [kW, DC bus]
        P_load_dc(t) = P_load(t) / eta_cnv         [kW, DC-referred]
        P_net_dc(t)  = P_ren_dc(t) - P_load_dc(t)  [kW, DC bus]

    Battery balance operates entirely on DC bus.
    η_cnv applied only at DC→AC inverter for load referral and
    for converting DC surplus/discharge to AC-equivalent for reporting.
    DG output is AC-side — not subject to η_cnv.

    Parameters
    ----------
    P_pv_arr   : array (kW) — PV output at DC bus (after DC/DC converter)
    P_wt_arr   : array (kW) — Wind output at DC bus (after AC/DC converter)
    P_load_arr : array (kW) — AC load demand
    E_bat_max  : float (kWh) — total nominal battery capacity
    N_dg       : int — number of diesel generator units
    eta_cnv    : float — central DC/AC inverter efficiency
    eta_BC     : float — battery charge efficiency (DC/DC + electrochemical)
    eta_BD     : float — battery discharge efficiency (DC/DC + electrochemical)
    DOD        : float — maximum depth of discharge
    sigma      : float — hourly self-discharge rate (h⁻¹)
    pdg_r      : float — per-unit DG rated power (kW)

    Returns
    -------
    dict — hourly arrays + annual AC-equivalent summaries + KPIs.
    """
    n_hours = 8760
    P_pv    = np.asarray(P_pv_arr,   dtype=float)
    P_wt    = np.asarray(P_wt_arr,   dtype=float)
    P_load  = np.asarray(P_load_arr, dtype=float)

    # ── Battery SOC limits — Eq.(16), Section 3.3 ────────────
    E_bat_min = (1 - DOD) * E_bat_max
    Eb        = 0.5 * E_bat_max     # Eq.(18): E_b(0) = 0.5 * E_bat_max

    # ── Total diesel rated capacity (AC bus) ──────────────────
    Pr_dg_total = N_dg * pdg_r

    # ── Output arrays ─────────────────────────────────────────
    # Energy reported in AC-equivalent kWh for LCOE/REP consistency.
    P_pv_out  = np.zeros(n_hours)   # DC generation (kW)
    P_wt_out  = np.zeros(n_hours)   # DC generation (kW)
    P_bat     = np.zeros(n_hours)   # DC: negative=charge, positive=discharge
    P_dg_out  = np.zeros(n_hours)   # AC generation (kW)
    P_dump    = np.zeros(n_hours)   # AC dump power (kW, after η_cnv)
    E_bat_soc = np.zeros(n_hours)   # Battery stored energy (kWh)
    LPS       = np.zeros(n_hours)   # Loss of power supply (kWh, AC)

    for t in range(n_hours):

        # ── DC-bus generation ─────────────────────────────────
        P_ren_dc   = P_pv[t] + P_wt[t]       # total DC renewable (kW)
        P_pv_out[t] = P_pv[t]
        P_wt_out[t] = P_wt[t]

        # ── AC load referred to DC bus — Section 3.3, Eq.(12)-(13) ──
        P_load_dc  = P_load[t] / eta_cnv      # DC-equivalent load (kW)

        # ── DC net power ──────────────────────────────────────
        P_net_dc   = P_ren_dc - P_load_dc

        if P_net_dc >= 0:
            # ── Scenario 1: DC surplus → charge battery ───────
            # DC surplus available for charging
            surplus_dc = P_net_dc

            # Maximum charge power limited by battery headroom
            P_charge   = min(surplus_dc,
                             (E_bat_max - Eb) / eta_BC)

            # Eq.(13): Eb(t+1) = Eb(t)*(1-σ) + P_charge*η_BC
            # Lower bound guard: self-discharge alone cannot push Eb
            # below E_bat_min even when P_charge ≈ 0.
            Eb = min(E_bat_max,
                     max(E_bat_min,
                         Eb * (1 - sigma) + P_charge * eta_BC))
            P_bat[t] = -P_charge   # negative = charging (DC)

            # ── Scenario 2: DC surplus > battery → dump load ──
            # Remaining DC surplus converted to AC via η_cnv
            # before reaching dump load (AC bus, Fig. 1)
            remaining_dc = surplus_dc - P_charge
            if remaining_dc > 1e-6:
                P_dump[t] = remaining_dc * eta_cnv   # AC dump (kW)

        else:
            # ── Scenario 3: DC deficit → battery discharges ───
            deficit_dc  = -P_net_dc

            # Available battery discharge in DC terms
            P_bat_avail = (Eb - E_bat_min) * eta_BD

            if P_bat_avail >= deficit_dc:
                # Battery covers full DC deficit
                P_discharge = deficit_dc
                # Eq.(12): Eb(t+1) = Eb(t)*(1-σ) - P_discharge/η_BD
                Eb = max(E_bat_min,
                         Eb * (1 - sigma) - P_discharge / eta_BD)
                P_bat[t] = P_discharge   # positive = discharging (DC)

            else:
                # Battery partially covers DC deficit
                P_discharge = P_bat_avail
                Eb = max(E_bat_min,
                         Eb * (1 - sigma) - P_discharge / eta_BD)
                P_bat[t] = P_discharge

                # Remaining deficit converted to AC domain
                # (battery discharge reaches AC bus via η_cnv;
                #  DG operates directly on AC bus)
                remaining_deficit_ac = (deficit_dc - P_discharge) * eta_cnv

                # ── Scenario 4: diesel covers AC remainder ────
                P_dg_t      = min(remaining_deficit_ac, Pr_dg_total)
                P_dg_out[t] = P_dg_t

                # Unmet AC demand → Loss of Power Supply
                unmet = remaining_deficit_ac - P_dg_t
                if unmet > 1e-6:
                    LPS[t] = unmet

        E_bat_soc[t] = Eb

    # ── Annual energy summaries (AC-equivalent kWh) ───────────
    # PV and wind DC generation converted to AC for energy accounting
    # consistent with LCOE denominator (E_load is AC).
    E_pv_annual   = P_pv_out.sum() * eta_cnv   # DC→AC equivalent
    E_wt_annual   = P_wt_out.sum() * eta_cnv   # DC→AC equivalent
    E_dg_annual   = P_dg_out.sum()             # already AC
    E_dump_annual = P_dump.sum()               # already AC
    E_load_annual = P_load.sum()               # AC
    LPS_total     = LPS.sum()                  # AC

    # ── LPSP — Eq.(35), Alsaqqar & Abuelrub (2026) ───────────
    LPSP = LPS_total / E_load_annual if E_load_annual > 0 else 1.0

    # ── REP — Eq.(38), Alsaqqar & Abuelrub (2026) ────────────
    # All quantities in AC-equivalent kWh
    E_ren = E_pv_annual + E_wt_annual
    REP   = (E_ren / (E_ren + E_dg_annual)
             if (E_ren + E_dg_annual) > 0 else 0.0)

    return {
        # Hourly arrays
        "P_pv_dc":       P_pv_out,             # DC generation (kW)
        "P_wt_dc":       P_wt_out,             # DC generation (kW)
        "P_bat":         P_bat,                # DC: neg=charge, pos=discharge
        "P_dg":          P_dg_out,             # AC generation (kW)
        "P_dump":        P_dump,               # AC dump power (kW)
        "E_bat_soc":     E_bat_soc,            # Battery energy (kWh)
        "LPS":           LPS,                  # Unmet AC demand (kWh)
        # Annual AC-equivalent summaries
        "E_pv_annual":   E_pv_annual,          # AC-equivalent kWh
        "E_wt_annual":   E_wt_annual,          # AC-equivalent kWh
        "E_dg_annual":   E_dg_annual,          # AC kWh
        "E_dump_annual": E_dump_annual,        # AC kWh
        "LPS_total":     LPS_total,            # AC kWh
        "E_load_annual": E_load_annual,        # AC kWh
        # Performance indicators
        "LPSP":          LPSP,
        "REP":           REP,
    }


# ── Verification (Dakhla, test sizing) ───────────────────────

_site        = "Dakhla, Morocco"
_N_pv, _N_wt = 100, 2

# PV — hybrid one-diode (Cell 4b)

# Wind — hub-height corrected (Cell 4)



# ── DC-bus sanity check ───────────────────────────────────────


# Cell 8: Fitness Function Wrapper (UPDATED for Cell 5)
# ============================================================
# Objective : minimize TNPC subject to reliability and
#             renewable energy constraints
#
# Decision variables (integer counts):
#   x = [N_pv, N_wt, N_bat, N_dg]
#
# Objective function — Eq.(28), Alsaqqar & Abuelrub (2026):
#   Min. TNPC(N_pv, N_wt, N_bat, N_dg)
#
# Constraints:
#   LPSP ≤ LPSP*  — Eq.(37), Alsaqqar & Abuelrub (2026)
#   REP  ≥ REP*   — Eq.(39), Alsaqqar & Abuelrub (2026)
#
# Constraint handling: static external penalty method
#   Ref: Deb, K. (2000). "An efficient constraint handling method
#        for genetic algorithms." Computer Methods in Applied
#        Mechanics and Engineering, 186(2-4), 311-338.
#   Penalty coefficient = 1e8 (≈ 100,000× typical TNPC magnitude)
#
# CO2 avoidance (diesel-displacement convention)
#   Ref: IPCC (2006). Guidelines for National GHG Inventories,
#        Vol. 2 (Energy), Ch. 3, Table 3.3.1.
#        Diesel emission factor = 2.68 kg CO2 / L
#   Baseline: diesel-only system sized to serve peak load.
#
# PV model  : hybrid one-diode (PV_UNIT_PROFILES, Cell 4b)
# Wind model: hub-height corrected (Cell 4)
# Converter : DC-side peak renewable generation (Mokhtara 2021)
# ============================================================

import numpy as np

# Battery unit size — 5 kWh Li-ion module
E_BAT_UNIT = 5.0

# CO2 emission factor for diesel — IPCC (2006)
DIESEL_CO2_KG_PER_L = 2.68


# ── Diesel-only baseline (cached per site) ───────────────────
_DIESEL_BASELINE_CACHE = {}

def compute_diesel_only_baseline(site_name, pdg_r_local=None):
    """
    Diesel-only baseline: a single DG sized just large enough to
    serve peak load, dispatched 1-for-1 against demand each hour.
    Returns annual fuel consumption (L/yr) for the same load.
    """
    if site_name in _DIESEL_BASELINE_CACHE:
        return _DIESEL_BASELINE_CACHE[site_name]

    pdg_r_loc = pdg_r_local if pdg_r_local is not None else pdg_r
    P_load    = LOAD_PROFILES[site_name]
    P_peak    = float(P_load.max())

    N_dg_base   = int(np.ceil(P_peak / pdg_r_loc))
    Pr_total    = N_dg_base * pdg_r_loc

    P_dg_arr = np.minimum(P_load, Pr_total)
    on_mask  = P_dg_arr > 1e-6
    F_dg_t   = np.where(
        on_mask,
        ALPHA_DG * Pr_total + BETA_DG * P_dg_arr,
        0.0)
    FC_baseline_L = float(F_dg_t.sum())

    _DIESEL_BASELINE_CACHE[site_name] = FC_baseline_L
    return FC_baseline_L


def evaluate_system(x, site_name,
                    LPSP_target = 0.05,
                    REP_target  = 0.5,
                    return_full = False):
    """
    Evaluate one candidate HRES configuration.

    Parameters
    ----------
    x            : array-like — [N_pv, N_wt, N_bat, N_dg]
    site_name    : str
    LPSP_target  : float — reliability constraint
    REP_target   : float — renewable penetration constraint
    return_full  : bool

    Returns
    -------
    fitness : float (and metrics dict if return_full=True)
    """

    # ── Step 1: Decode decision variables ─────────────────────
    N_pv, N_wt, N_bat, N_dg = [int(round(v)) for v in x]
    N_pv  = max(0, N_pv)
    N_wt  = max(0, N_wt)
    N_bat = max(0, N_bat)
    N_dg  = max(0, N_dg)

    E_bat_max = N_bat * E_BAT_UNIT

    # ── Step 2: Site weather + load ───────────────────────────
    df     = all_site_data[site_name]
    P_load = LOAD_PROFILES[site_name]

    # ── Step 3: Renewable generation ──────────────────────────
    # PV — hybrid one-diode (Cell 4b)
    P_pv_raw = pv_power_output(PV_UNIT_PROFILES[site_name], N_pv)

    # Wind — hub-height corrected (Cell 4)
    V_hub    = wind_speed_hub(
        df["wind_speed"].values,
        H_hub  = WT_PARAMS["H_hub"],
        H_ref  = WT_PARAMS["H_ref"],
        alpha  = WT_PARAMS["alpha"])
    P_wt_raw = wind_power(
        V_hub,
        WT_PARAMS["Pr"] * N_wt,
        WT_PARAMS["Vcutin"],
        WT_PARAMS["Vrated"],
        WT_PARAMS["Vcutout"])

    # ── Step 4: EMS dispatch ──────────────────────────────────
    E_bat_eff = E_bat_max if E_bat_max > 1e-3 else 1e-3
    ems = run_EMS(
        P_pv_arr   = P_pv_raw,
        P_wt_arr   = P_wt_raw,
        P_load_arr = P_load,
        E_bat_max  = E_bat_eff,
        N_dg       = N_dg)

    # ── Step 5: Converter sizing (DC-side peak generation) ───
    P_cnv_kW = float((P_pv_raw + P_wt_raw).max())

    # ── Step 6: TNPC using UPDATED compute_TNPC (Cell 5) ──────
    # New signature: compute_TNPC(site_name, N_pv, N_wt, E_bat_kWh, N_dg, P_cnv_kW, P_dg_arr)
    tnpc_result = compute_TNPC(
        site_name  = site_name,
        N_pv       = N_pv,
        N_wt       = N_wt,
        E_bat_kWh  = E_bat_max,
        N_dg       = N_dg,
        P_cnv_kW   = P_cnv_kW,
        P_dg_arr   = ems["P_dg"]
    )
    TNPC_total = tnpc_result["TNPC_total"]
    FC_actual_L = tnpc_result["FC_annual_L"]
    CRF_site = tnpc_result["CRF"]   # CRF from site-specific economics

    # ── Step 7: Performance indicators ───────────────────────
    E_load = ems["E_load_annual"]
    E_ren  = ems["E_pv_annual"] + ems["E_wt_annual"]
    E_dg   = ems["E_dg_annual"]

    LPSP = ems["LPS_total"] / E_load if E_load > 0 else 1.0
    REP = E_ren / (E_ren + E_dg) if (E_ren + E_dg) > 0 else 0.0

    # LCOE — UPDATED: compute_LCOE now requires CRF
    # compute_LCOE(TNPC_total, E_load_annual_kWh, CRF)
    LCOE = compute_LCOE(TNPC_total, E_load, CRF_site)

    # DSF — fraction of hours with no unmet load
    hours_met = float(np.sum(ems["LPS"] < 1e-6))
    DSF = hours_met / 8760.0

    # CDRA — diesel-displacement
    FC_baseline_L = compute_diesel_only_baseline(site_name)
    fuel_saved_L  = max(0.0, FC_baseline_L - FC_actual_L)
    CDRA = fuel_saved_L * DIESEL_CO2_KG_PER_L / 1000.0   # tCO2/yr

    # ── Step 8: Constraint penalty (Deb 2000) ─────────────────
    PENALTY_COEF = 1e8
    penalty = 0.0
    if LPSP > LPSP_target:
        penalty += PENALTY_COEF * (LPSP - LPSP_target)
    if REP < REP_target:
        penalty += PENALTY_COEF * (REP_target - REP)

    # ── Step 9: Fitness ───────────────────────────────────────
    fitness = TNPC_total + penalty

    # ── Step 10: Return ───────────────────────────────────────
    if return_full:
        return fitness, {
            # Decision variables
            "N_pv":           N_pv,
            "N_wt":           N_wt,
            "N_bat":          N_bat,
            "N_dg":           N_dg,
            "E_bat_kWh":      E_bat_max,
            "P_cnv_kW":       P_cnv_kW,
            # Economic
            "TNPC":           TNPC_total,
            "LCOE":           LCOE,
            "TNPC_breakdown": tnpc_result,
            "FC_actual_L":    FC_actual_L,
            "FC_baseline_L":  FC_baseline_L,
            "CRF":            CRF_site,
            # Reliability
            "LPSP":           LPSP,
            "REP":            REP,
            "DSF":            DSF,
            # Environmental
            "fuel_saved_L":   fuel_saved_L,
            "CDRA":           CDRA,
            # Constraint
            "penalty":        penalty,
            "feasible":       (penalty == 0.0),
            # EMS
            "ems":            ems,
        }

    return fitness


# ── Decision variable bounds ──────────────────────────────────
BOUNDS = {
    "N_pv":  (0, 1000),   # 200W panels → up to 200 kW
    "N_wt":  (0, 20),     # 100 kW each → up to 2 MW
    "N_bat": (0, 200),    # 5 kWh each  → up to 1 MWh
    "N_dg":  (0, 20),     # 10 kW each  → up to 200 kW
}
LB = np.array([b[0] for b in BOUNDS.values()])
UB = np.array([b[1] for b in BOUNDS.values()])


# ── Verification ──────────────────────────────────────────────

# ── Pre-compute diesel-only baselines for all sites ──────────


x_test = [200, 2, 40, 10]



# Cell 9a: Particle Swarm Optimization (PSO)
# ============================================================
# Ref: Alsaqqar & Abuelrub (2026), Section 3.1, Eqs.(57)-(59)
#      Original PSO: Kennedy & Eberhart (1995), ICNN'95
#      Velocity clamping: Eberhart & Shi (2000), CEC'00, p.84-88
#
# Velocity update — Eq.(57):
#   v_ij(t) = w*v_ij(t-1) + c1*r1*(Pbest_ij(t-1) - X_ij(t-1))
#                          + c2*r2*(Gbest_ij(t-1) - X_ij(t-1))
#
# Position update — Eq.(58):
#   X_ij(t) = X_ij(t-1) + v_ij(t)
#
# Inertia weight — Eq.(59):
#   ω = ω_max - ((ω_max - ω_min) / Iter_max) * Iter
#   ω decreases linearly from 0.9 (it=0) toward 0.4
#
# Parameters — Alsaqqar & Abuelrub (2026), Section 3.1:
#   ω_max = 0.9, ω_min = 0.4, c1 = c2 = 2.0
#
# Implementation choices (disclosed in manuscript):
#   - n_particles = 30, n_iter = 100
#     (reference uses 200×50; we use 30×100 to balance compute
#      across 51,840 runs; total function evals comparable.)
#   - Boundary handling: clip positions to [LB, UB]
#     (required: decision variables are discrete component
#     counts that must remain in feasible bounds)
#   - Velocity clamping: v_max = 0.2 × range
#     Ref: Eberhart, R.C. & Shi, Y. (2000). "Comparing inertia
#     weights and constriction factors in PSO." Proc. CEC, 84-88.
#     (standard PSO safeguard against velocity explosion)
#   - Integer rounding: np.round().astype(int)
#     (decision variables are component counts ∈ ℤ⁺)
#   - Non-finite guard: replace inf/nan fitness with 1e12
# ============================================================

import numpy as np
import time


def pso_optimize(site_name,
                 LPSP_target = 0.05,
                 REP_target  = 0.5,
                 n_particles = 30,
                 n_iter      = 100,
                 w_max       = 0.9,
                 w_min       = 0.4,
                 c1          = 2.0,
                 c2          = 2.0,
                 v_max_frac  = 0.2,
                 seed        = 42,
                 verbose     = True,
                 record_diversity = True):
    """
    Particle Swarm Optimization for HRES sizing.

    Implements Eqs.(57)-(59) of Alsaqqar & Abuelrub (2026),
    augmented with standard implementation safeguards
    (boundary clipping, velocity clamping per Eberhart & Shi 2000,
    integer rounding for discrete component counts).

    Parameters
    ----------
    site_name        : str   — site key in all_site_data
    LPSP_target      : float — reliability constraint, Eq.(37)
    REP_target       : float — renewable portion constraint, Eq.(39)
    n_particles      : int   — swarm size
    n_iter           : int   — maximum iterations
    w_max, w_min     : float — inertia weight bounds (Eq. 59)
    c1, c2           : float — cognitive, social coefficients (Eq. 57)
    v_max_frac       : float — velocity clamp as fraction of range
                              (Eberhart & Shi, 2000)
    seed             : int   — RNG seed for reproducibility
    verbose          : bool  — print progress every 10 iterations
    record_diversity : bool  — track swarm spatial diversity

    Returns
    -------
    dict with keys:
        site, algorithm, x_best, fitness, metrics, history,
        diversity, n_func_evals, runtime_sec, settings,
        LPSP_target, REP_target, seed
    """
    # ── Reproducibility ──────────────────────────────────────
    rng       = np.random.default_rng(seed)
    n_dim     = len(LB)
    v_max     = v_max_frac * (UB - LB)
    n_evals   = 0
    t_start   = time.time()

    # ── Initialize swarm ──────────────────────────────────────
    X = rng.uniform(LB, UB, size=(n_particles, n_dim))
    V = rng.uniform(-v_max, v_max, size=(n_particles, n_dim))

    fitness = np.array([
        evaluate_system(np.round(X[i]).astype(int),
                        site_name, LPSP_target, REP_target)
        for i in range(n_particles)
    ])
    fitness = np.where(np.isfinite(fitness), fitness, 1e12)
    n_evals += n_particles

    Pbest      = X.copy()
    Pbest_fit  = fitness.copy()
    g_idx      = int(np.argmin(Pbest_fit))
    Gbest      = Pbest[g_idx].copy()
    Gbest_fit  = float(Pbest_fit[g_idx])

    # ── Tracking ──────────────────────────────────────────────
    history    = [Gbest_fit]
    diversity  = [_swarm_diversity(X)] if record_diversity else None

    # ── Main loop ─────────────────────────────────────────────
    for it in range(n_iter):

        # Inertia weight — Eq.(59) verbatim
        # ω = ω_max - ((ω_max - ω_min) / Iter_max) * Iter
        w = w_max - (w_max - w_min) * (it / n_iter)

        # Stochastic coefficients
        r1 = rng.random((n_particles, n_dim))
        r2 = rng.random((n_particles, n_dim))

        # Velocity update — Eq.(57)
        V = (w * V
             + c1 * r1 * (Pbest - X)
             + c2 * r2 * (Gbest - X))

        # Velocity clamping — Eberhart & Shi (2000)
        V = np.clip(V, -v_max, v_max)

        # Position update — Eq.(58), with bound clipping
        X = np.clip(X + V, LB, UB)

        # Evaluate
        fitness = np.array([
            evaluate_system(np.round(X[i]).astype(int),
                            site_name, LPSP_target, REP_target)
            for i in range(n_particles)
        ])
        fitness = np.where(np.isfinite(fitness), fitness, 1e12)
        n_evals += n_particles

        # Update personal best
        improved             = fitness < Pbest_fit
        Pbest[improved]      = X[improved]
        Pbest_fit[improved]  = fitness[improved]

        # Update global best
        g_idx = int(np.argmin(Pbest_fit))
        if Pbest_fit[g_idx] < Gbest_fit:
            Gbest     = Pbest[g_idx].copy()
            Gbest_fit = float(Pbest_fit[g_idx])

        history.append(Gbest_fit)
        if record_diversity:
            diversity.append(_swarm_diversity(X))

        if verbose and (it + 1) % 10 == 0:
            div_str = (f"div={diversity[-1]:>6.2f}  "
                       if record_diversity else "")
            print(f"  iter {it+1:>3}/{n_iter} | "
                  f"w={w:.3f} | {div_str}"
                  f"best = ${Gbest_fit:>14,.2f}")

    runtime = time.time() - t_start

    # ── Extract best solution with full metrics ──────────────
    Gbest_int = np.round(Gbest).astype(int)
    _, best_metrics = evaluate_system(
        Gbest_int, site_name,
        LPSP_target, REP_target, return_full=True)
    n_evals += 1

    return {
        # Identification
        "site":         site_name,
        "algorithm":    "PSO",
        "seed":         seed,
        # Solution
        "x_best":       Gbest_int,
        "fitness":      Gbest_fit,
        "metrics":      best_metrics,
        # Constraint targets
        "LPSP_target":  LPSP_target,
        "REP_target":   REP_target,
        # Performance tracking (Q1 metadata)
        "history":      np.array(history),
        "diversity":    (np.array(diversity)
                         if record_diversity else None),
        "n_func_evals": n_evals,
        "runtime_sec":  runtime,
        # Algorithm settings (reproducibility)
        "settings": {
            "n_particles": n_particles,
            "n_iter":      n_iter,
            "w_max":       w_max,
            "w_min":       w_min,
            "c1":          c1,
            "c2":          c2,
            "v_max_frac":  v_max_frac,
        },
    }


def _swarm_diversity(X):
    """
    Spatial diversity of swarm: mean distance from centroid.
    Used to monitor exploration vs. exploitation balance.
    Ref: Olorunda & Engelbrecht (2008), "Measuring exploration/
         exploitation in PSO." Proc. IEEE CEC, 1128-1134.
    """
    centroid = np.mean(X, axis=0)
    return float(np.mean(np.linalg.norm(X - centroid, axis=1)))


# ── Verification ──────────────────────────────────────────────




# Cell 9b: Grey Wolf Optimizer (GWO)
# ============================================================
# Ref: Mirjalili, S., Mirjalili, S.M., & Lewis, A. (2014).
#      "Grey Wolf Optimizer."
#      Advances in Engineering Software 69:46-61.
#      DOI: 10.1016/j.advengsoft.2013.12.007
#
# AI-ASSISTED IMPLEMENTATION:
#   This cell was developed with AI assistance (Claude, Anthropic)
#   based on the canonical equations of Mirjalili et al. (2014).
#   Leader-update logic was corrected after senior-reviewer audit
#   to use combined-sort (pool + top-3) approach, preserving the
#   hierarchy invariant α ≤ β ≤ δ. All equations were verified by
#   the authors against the cited source.
#   Disclosed in manuscript Methods section.
#
# ── EXACT EQUATIONS (Mirjalili et al. 2014) ───────────────────
#
# Encircling distance — Eq.(3.1):
#   D = |C * X_p(t) - X(t)|
#
# Position update (single-leader form) — Eq.(3.2):
#   X(t+1) = X_p(t) - A * D
#   Note: subsumed by three-leader form (3.5)-(3.7) below.
#
# Coefficient A — Eq.(3.3):
#   A = 2*a*r1 - a
#   where r1 ∈ [0,1]^d random vector
#
# Coefficient C — Eq.(3.4):
#   C = 2*r2
#   where r2 ∈ [0,1]^d random vector
#
# Linear control parameter a — Mirjalili 2014, page 49 text:
#   a = 2 - 2*(t / T_max)
#   linearly decreases from 2 to 0 over iterations
#
# Three-leader distances — Eq.(3.5):
#   D_alpha = |C1 * X_alpha - X|
#   D_beta  = |C2 * X_beta  - X|
#   D_delta = |C3 * X_delta - X|
#
# Three candidate positions — Eq.(3.6):
#   X1 = X_alpha - A1 * D_alpha
#   X2 = X_beta  - A2 * D_beta
#   X3 = X_delta - A3 * D_delta
#
# Final position update — Eq.(3.7):
#   X(t+1) = (X1 + X2 + X3) / 3
#
# Exploration vs. exploitation:
#   |A| > 1 : wolves diverge from prey (exploration)
#   |A| < 1 : wolves converge on prey  (exploitation)
#
# Algorithm 1 (Fig. 6) structure:
#   - Sort population, identify alpha/beta/delta
#   - For each wolf: compute D_alpha, D_beta, D_delta (Eq. 3.5)
#   - For each wolf: compute X1, X2, X3 (Eq. 3.6)
#   - For each wolf: update position via Eq.(3.7)
#   - Re-evaluate all wolves
#   - Update alpha/beta/delta (canonical: re-sort + elitism)
#
# Random sampling (canonical reference MATLAB convention):
#   6 fresh r-vectors per wolf per iteration:
#   3 leaders × 2 vectors (r1, r2) each = 6 total.
#
# Implementation safeguards (consistent with Cells 9a, 9d):
#   - Boundary clipping: positions clipped to [LB, UB]
#     (required for integer-count problem; not in source)
#   - Integer rounding: np.round().astype(int)
#     (decision variables are component counts ∈ ℤ⁺)
#   - Non-finite guard: replace inf/nan fitness with 1e12
#   - Leader update: pool current population with stored leaders
#     and take top 3 (preserves α ≤ β ≤ δ invariant + elitism)
# ============================================================

import numpy as np
import time


def gwo_optimize(site_name,
                 LPSP_target = 0.05,
                 REP_target  = 0.5,
                 n_wolves    = 30,
                 n_iter      = 100,
                 seed        = 42,
                 verbose     = True,
                 record_diversity = True):
    """
    Grey Wolf Optimizer for HRES sizing.

    Implements Algorithm 1 of Mirjalili et al. (2014),
    Eqs.(3.1)-(3.7), with implementation safeguards consistent
    with Cell 9a (PSO) and Cell 9d (APO-PSO).

    Leader update uses pool-and-sort approach: at each iteration,
    the current population is pooled with the stored α, β, δ from
    the previous iteration, and the top three of this combined pool
    become the new α, β, δ. This is provably correct (preserves
    α ≤ β ≤ δ invariant) and provides elitism for free.

    Parameters
    ----------
    site_name        : str   — site key in all_site_data
    LPSP_target      : float — reliability constraint
    REP_target       : float — renewable portion constraint
    n_wolves         : int   — population size
    n_iter           : int   — maximum iterations T_max
    seed             : int   — RNG seed for reproducibility
    verbose          : bool  — print progress every 10 iterations
    record_diversity : bool  — track population spatial diversity

    Returns
    -------
    dict — same structure as Cell 9a (PSO) and Cell 9d (APO-PSO).
    """
    # ── Reproducibility ──────────────────────────────────────
    rng     = np.random.default_rng(seed)
    n_dim   = len(LB)
    T_max   = n_iter
    n_evals = 0
    t_start = time.time()

    # ── Initialize wolf pack (Algorithm 1, line 1) ───────────
    X = rng.uniform(LB, UB, size=(n_wolves, n_dim))

    # Evaluate initial fitness
    fitness = np.array([
        evaluate_system(np.round(X[i]).astype(int),
                        site_name, LPSP_target, REP_target)
        for i in range(n_wolves)
    ])
    fitness = np.where(np.isfinite(fitness), fitness, 1e12)
    n_evals += n_wolves

    # Identify alpha (best), beta (2nd), delta (3rd) wolves
    sorted_idx = np.argsort(fitness)
    X_alpha    = X[sorted_idx[0]].copy()
    X_beta     = X[sorted_idx[1]].copy()
    X_delta    = X[sorted_idx[2]].copy()
    f_alpha    = float(fitness[sorted_idx[0]])
    f_beta     = float(fitness[sorted_idx[1]])
    f_delta    = float(fitness[sorted_idx[2]])

    # ── Tracking ──────────────────────────────────────────────
    history   = [f_alpha]
    a_log     = [2.0]
    diversity = [_swarm_diversity(X)] if record_diversity else None

    # ── Main loop (Algorithm 1, line 5) ──────────────────────
    for t in range(T_max):

        # Linear control parameter — Mirjalili 2014, page 49
        # a = 2 - 2*(t / T_max), decreases from 2 toward 0
        a = 2.0 - 2.0 * (t / T_max)

        # Inner loop over wolves (Algorithm 1, line 7)
        # Note: Eq.(3.2) X(t+1) = X_p − A·D is the single-leader
        # encircling form. The algorithm uses the three-leader
        # hunting form Eqs.(3.5)-(3.7), which subsumes Eq.(3.2)
        # (when α = β = δ, the three-leader form reduces to it).
        for i in range(n_wolves):

            # ── Compute distances to leaders — Eq.(3.5) ──────
            # 6 fresh r-vectors per wolf: 3 leaders × 2 each
            r1_a = rng.random(n_dim);  r2_a = rng.random(n_dim)
            r1_b = rng.random(n_dim);  r2_b = rng.random(n_dim)
            r1_d = rng.random(n_dim);  r2_d = rng.random(n_dim)

            # Coefficients A and C for each leader — Eqs.(3.3)-(3.4)
            A1 = 2*a*r1_a - a;  C1 = 2*r2_a
            A2 = 2*a*r1_b - a;  C2 = 2*r2_b
            A3 = 2*a*r1_d - a;  C3 = 2*r2_d

            # Distances to leaders — Eq.(3.5)
            D_alpha = np.abs(C1 * X_alpha - X[i])
            D_beta  = np.abs(C2 * X_beta  - X[i])
            D_delta = np.abs(C3 * X_delta - X[i])

            # ── Candidate positions — Eq.(3.6) ───────────────
            X1 = X_alpha - A1 * D_alpha
            X2 = X_beta  - A2 * D_beta
            X3 = X_delta - A3 * D_delta

            # ── Final position — Eq.(3.7) ────────────────────
            X_new = (X1 + X2 + X3) / 3.0

            # Boundary clipping (safeguard, not in source)
            X_new = np.clip(X_new, LB, UB)

            # Update wolf position
            X[i] = X_new

        # ── Re-evaluate all wolves (Algorithm 1, line 9) ─────
        fitness = np.array([
            evaluate_system(np.round(X[i]).astype(int),
                            site_name, LPSP_target, REP_target)
            for i in range(n_wolves)
        ])
        fitness = np.where(np.isfinite(fitness), fitness, 1e12)
        n_evals += n_wolves

        # ── Update alpha/beta/delta (Algorithm 1, line 10) ──
        # Pool current population with stored leaders, take top 3.
        # This combines elitism (never lose best solutions) with
        # the canonical Mirjalili 2014 update, while provably
        # maintaining the hierarchy invariant α ≤ β ≤ δ.
        pool_X = np.vstack([X,
                            X_alpha[np.newaxis, :],
                            X_beta[np.newaxis, :],
                            X_delta[np.newaxis, :]])
        pool_f = np.concatenate([fitness,
                                 [f_alpha, f_beta, f_delta]])
        top3   = np.argsort(pool_f)[:3]

        X_alpha = pool_X[top3[0]].copy()
        X_beta  = pool_X[top3[1]].copy()
        X_delta = pool_X[top3[2]].copy()
        f_alpha = float(pool_f[top3[0]])
        f_beta  = float(pool_f[top3[1]])
        f_delta = float(pool_f[top3[2]])

        history.append(f_alpha)
        a_log.append(a)
        if record_diversity:
            diversity.append(_swarm_diversity(X))

        if verbose and (t + 1) % 10 == 0:
            div_str = (f"div={diversity[-1]:>6.2f}  "
                       if record_diversity else "")
            print(f"  iter {t+1:>3}/{T_max} | "
                  f"a={a:.3f} | {div_str}"
                  f"best = ${f_alpha:>14,.2f}")

    runtime = time.time() - t_start

    # ── Extract best solution with full metrics ──────────────
    X_alpha_int = np.round(X_alpha).astype(int)
    _, best_metrics = evaluate_system(
        X_alpha_int, site_name,
        LPSP_target, REP_target, return_full=True)
    n_evals += 1

    return {
        # Identification
        "site":         site_name,
        "algorithm":    "GWO",
        "seed":         seed,
        # Solution
        "x_best":       X_alpha_int,
        "fitness":      f_alpha,
        "metrics":      best_metrics,
        # Constraint targets
        "LPSP_target":  LPSP_target,
        "REP_target":   REP_target,
        # Performance tracking (Q1 metadata)
        "history":      np.array(history),
        "a_log":        np.array(a_log),
        "diversity":    (np.array(diversity)
                         if record_diversity else None),
        "n_func_evals": n_evals,
        "runtime_sec":  runtime,
        # Algorithm settings
        "settings": {
            "n_wolves": n_wolves,
            "n_iter":   n_iter,
        },
    }


# Note: _swarm_diversity() is defined in Cell 9a (PSO).
# Reused here for consistent diversity metrics across all algorithms.


# ── Verification ──────────────────────────────────────────────






# Cell 9c: Arctic Puffin Optimization (APO) - CORRECTED
# ============================================================
# Ref: Wang, W., Tian, W., Xu, D., & Zang, H. (2024).
#      "Arctic puffin optimization: A bio-inspired metaheuristic
#       algorithm for solving engineering design optimization."
#      Advances in Engineering Software 195:103694.
#      DOI: 10.1016/j.advengsoft.2024.103694
#
# ── EXACT EQUATIONS (Wang et al. 2024) ────────────────────────
#
# Population initialization — Eq.(1):
#   X_i = rand * (ub - lb) + lb,   i = 1, 2, ..., N
#   rand ∈ (0,1) scalar; ub, lb are upper/lower bound vectors.
#
# ── AERIAL FLIGHT STAGE (Exploration), used when B > C ──
#
# Aerial search — Eq.(2):
#   Y_i(t+1) = X_i(t) + (X_i(t) - X_r(t)) * L(D) + R
#   where r ∈ {1,...,N-1}\{i}, X_r ≠ X_i.
#
# Random component — Eq.(3):
#   R = round(0.5 * (0.05 + rand)) * α
#
# Random scalar — Eq.(4):
#   α ~ Normal(0, 1)
#
# Swooping predation — Eq.(5):
#   Z_i(t+1) = Y_i(t+1) * S
#
# Velocity coefficient — Eq.(6):
#   S = tan((rand - 0.5) * π)
#
# Population merge & selection — Eqs.(7)-(9):
#   P_i(t+1) = Y_i(t+1) ∪ Z_i(t+1)
#   new      = sort(P_i(t+1))            (ascending by fitness)
#   X_i(t+1) = new(1 : N)                (top N survive)
#
# ── UNDERWATER FORAGING STAGE (Exploitation), used when B ≤ C ──
#
# Gathering foraging — Eq.(10):
#   W_i(t+1) = X_r1 + F * L(D) * (X_r2 - X_r3),    if rand ≥ 0.5
#   W_i(t+1) = X_r1 + F *        (X_r2 - X_r3),    if rand < 0.5
#   r1, r2, r3 distinct indices in {1,...,N-1}\{i}; X_r2 ≠ X_r3.
#   F = 0.5 (cooperative factor, paper §3.3.1 sensitivity result).
#
# Intensifying search — Eq.(11):
#   Y_i(t+1) = W_i(t+1) * (1 + f)
#
# Adaptive factor — Eq.(12):
#   f = 0.1 * (rand - 1) * (T - t) / T
#
# Avoiding predators — Eq.(13):
#   Z_i(t+1) = X_i + F * L(D) * (X_r1 - X_r2),    if rand ≥ 0.5
#   Z_i(t+1) = X_i + β        * (X_r1 - X_r2),    if rand < 0.5
#   β ~ U(0, 1) uniform scalar.
#
# Population merge & selection — Eqs.(14)-(16):
#   P_i(t+1) = W_i(t+1) ∪ Y_i(t+1) ∪ Z_i(t+1)
#   new      = sort(P_i(t+1))
#   X_i(t+1) = new(1 : N)
#
# ── BEHAVIORAL CONVERSION FACTOR ──
#
# Eq.(17):
#   B = 2 * log(1/rand) * (1 - t/T)
#   rand ∈ (0,1).
#   If B > C : exploration (aerial flight)
#   If B ≤ C : exploitation (underwater foraging)
#   C = 0.5 (paper §3.3.2 sensitivity result).
#
# ── ALGORITHM 1 STRUCTURE (Fig. 5, page 10) ──
#
#   1. Initialize N puffins via Eq.(1)
#   2. Evaluate fitness, identify best
#   3. while t < T:
#        4. Compute B via Eq.(17)
#        5. if B > C:                      ← exploration branch
#             for i = 1..N:
#               update Y_i via Eq.(2)
#               update Z_i via Eq.(5)
#             select new pop via Eqs.(7)-(9)
#             evaluate; replace if improved
#        6. else:                          ← exploitation branch
#             for i = 1..N:
#               update W_i via Eq.(10)
#               update Y_i via Eq.(11)
#               update Z_i via Eq.(13)
#             select new pop via Eqs.(14)-(16)
#             evaluate; replace if improved
#        7. t = t + 1
#   8. return best
#
# ── LEVY FLIGHT L(D) ──
#
# The paper cites refs [68-71] for Levy flight but does not give
# the closed-form expression. The canonical implementation in the
# cited literature, and in the official APO reference MATLAB code
# (MathWorks File Exchange #167521, linked in the paper footnote
# on page 1), is the Mantegna (1994) algorithm with β = 1.5:
#
#   L(D) = 0.01 * u / |v|^(1/β)
#   u ~ N(0, σ_u²),  v ~ N(0, 1)
#   σ_u = [ Γ(1+β) * sin(π*β/2) /
#           ( Γ((1+β)/2) * β * 2^((β-1)/2) ) ] ^ (1/β)
#
# We use Mantegna β = 1.5 for fidelity to the cited APO MATLAB
# reference and the broader Levy-flight swarm literature.
# This is an implementation choice (disclosed) — same disclosure
# pattern as v_max_frac (Cell 9a) and λ-formula (Cell 9d).
#
# ── IMPLEMENTATION SAFEGUARDS (consistent with Cells 9a, 9b, 9d) ──
#
#   - Boundary clipping  : positions clipped to [LB, UB]
#                          (required for integer-count problem)
#   - Integer rounding   : np.round().astype(int) on evaluation
#                          (decision variables ∈ ℤ⁺)
#   - Non-finite guard   : replace inf/nan fitness with 1e12
#   - Population update  : full replacement with top-N candidates
#                          (no index-wise mismatch)
#   - Levy-flight scope  : applied component-wise (vector L(D)),
#                          consistent with refs [68-71].
# ============================================================

import numpy as np
import time
from math import gamma, pi, sin


def apo_optimize(site_name,
                 LPSP_target=0.05,
                 REP_target=0.5,
                 n_puffins=30,
                 n_iter=100,
                 F=0.5,          # synergy factor, paper §3.3.1
                 C=0.5,          # threshold,      paper §3.3.2
                 beta_levy=1.5,  # Mantegna β,     refs [68-71]
                 seed=42,
                 verbose=True,
                 record_diversity=True):
    """
    Arctic Puffin Optimization for HRES sizing.

    Implements Algorithm 1 of Wang et al. (2024), Eqs.(1)-(17),
    with implementation safeguards consistent with Cells 9a (PSO),
    9b (GWO), and 9d (APO-PSO).

    Levy flight L(D) uses the Mantegna (1994) algorithm with
    β = 1.5, matching the official APO reference MATLAB code
    (MathWorks #167521) cited in the paper.

    Parameters
    ----------
    site_name        : str   — site key in all_site_data
    LPSP_target      : float — reliability constraint
    REP_target       : float — renewable portion constraint
    n_puffins        : int   — population size N
    n_iter           : int   — maximum iterations T
    F                : float — synergy factor (paper Table 2: 0.5)
    C                : float — behavioral threshold (paper Table 3: 0.5)
    beta_levy        : float — Mantegna stability index (1.5)
    seed             : int   — RNG seed for reproducibility
    verbose          : bool  — print progress every 10 iterations
    record_diversity : bool  — track population spatial diversity

    Returns
    -------
    dict — same structure as Cells 9a, 9b, 9d for consistent comparison.
    """
    # ── Reproducibility ──────────────────────────────────────
    rng = np.random.default_rng(seed)
    n_dim = len(LB)
    T = n_iter
    n_evals = 0
    t_start = time.time()

    # Mantegna σ_u for Levy flight (constant; depends only on β)
    sigma_u = (gamma(1 + beta_levy) * sin(pi * beta_levy / 2) /
               (gamma((1 + beta_levy) / 2) *
                beta_levy * 2 ** ((beta_levy - 1) / 2))) ** (1 / beta_levy)

    def levy(d):
        """Mantegna Levy flight, vector of length d."""
        u = rng.normal(0.0, sigma_u, size=d)
        v = rng.normal(0.0, 1.0, size=d)
        return 0.01 * u / (np.abs(v) ** (1 / beta_levy))

    def eval_one(x):
        """Evaluate one candidate solution with safeguards."""
        f = evaluate_system(np.round(x).astype(int),
                            site_name, LPSP_target, REP_target)
        return f if np.isfinite(f) else 1e12

    # ── Initialize population — Eq.(1) ────────────────────────
    X = rng.uniform(LB, UB, size=(n_puffins, n_dim))
    fitness = np.array([eval_one(X[i]) for i in range(n_puffins)])
    n_evals += n_puffins

    # Best so far
    g_idx = int(np.argmin(fitness))
    Gbest = X[g_idx].copy()
    Gbest_fit = float(fitness[g_idx])

    # ── Tracking ──────────────────────────────────────────────
    history = [Gbest_fit]
    B_log = [np.nan]               # B not yet computed at t=0
    phase_log = []                 # 'explore' / 'exploit' per iter
    diversity = [_swarm_diversity(X)] if record_diversity else None

    # ── Main loop (Algorithm 1, line 4) ──────────────────────
    for t in range(T):

        # Behavioral conversion factor — Eq.(17)
        rand_B = rng.random()
        rand_B = max(rand_B, 1e-12)
        B = 2.0 * np.log(1.0 / rand_B) * (1.0 - t / T)

        # ──────────────────────────────────────────────────────
        # EXPLORATION: aerial flight, when B > C
        # ──────────────────────────────────────────────────────
        if B > C:
            phase_log.append('explore')

            Y = np.empty_like(X)
            Z = np.empty_like(X)

            for i in range(n_puffins):
                # Pick r ≠ i (Eq. 2: "X_r ≠ X_i")
                r = rng.integers(n_puffins)
                while r == i:
                    r = rng.integers(n_puffins)

                # R = round(0.5*(0.05 + rand)) * α  — Eqs.(3)-(4)
                alpha = rng.normal(0.0, 1.0)
                R = round(0.5 * (0.05 + rng.random())) * alpha

                # Y_i — Eq.(2)
                Y[i] = X[i] + (X[i] - X[r]) * levy(n_dim) + R

                # Z_i — Eqs.(5)-(6)
                S = np.tan((rng.random() - 0.5) * np.pi)
                Z[i] = Y[i] * S

            # Bound clipping (safeguard, not in source)
            Y = np.clip(Y, LB, UB)
            Z = np.clip(Z, LB, UB)

            # Evaluate both candidate sets
            fY = np.array([eval_one(Y[i]) for i in range(n_puffins)])
            fZ = np.array([eval_one(Z[i]) for i in range(n_puffins)])
            n_evals += 2 * n_puffins

            # Merge Y ∪ Z, sort, take top N — Eqs.(7)-(9)
            pool_X = np.vstack([Y, Z])
            pool_f = np.concatenate([fY, fZ])
            top_N = np.argsort(pool_f)[:n_puffins]
            X_new = pool_X[top_N]
            f_new = pool_f[top_N]

        # ──────────────────────────────────────────────────────
        # EXPLOITATION: underwater foraging, when B ≤ C
        # ──────────────────────────────────────────────────────
        else:
            phase_log.append('exploit')

            W = np.empty_like(X)
            Y = np.empty_like(X)
            Z = np.empty_like(X)

            for i in range(n_puffins):
                # Pick r1, r2, r3 distinct, all ≠ i — Eq.(10) constraints
                pool = [j for j in range(n_puffins) if j != i]
                r1, r2, r3 = rng.choice(pool, size=3, replace=False)

                # Gathering foraging — Eq.(10)
                if rng.random() >= 0.5:
                    W[i] = X[r1] + F * levy(n_dim) * (X[r2] - X[r3])
                else:
                    W[i] = X[r1] + F * (X[r2] - X[r3])

                # Intensifying search — Eqs.(11)-(12)
                f_factor = 0.1 * (rng.random() - 1.0) * (T - t) / T
                Y[i] = W[i] * (1.0 + f_factor)

                # Avoiding predators — Eq.(13)
                r1p, r2p = rng.choice(pool, size=2, replace=False)
                if rng.random() >= 0.5:
                    Z[i] = X[i] + F * levy(n_dim) * (X[r1p] - X[r2p])
                else:
                    beta_unif = rng.random()    # β ~ U(0,1), Eq.(13)
                    Z[i] = X[i] + beta_unif * (X[r1p] - X[r2p])

            # Bound clipping
            W = np.clip(W, LB, UB)
            Y = np.clip(Y, LB, UB)
            Z = np.clip(Z, LB, UB)

            # Evaluate all three candidate sets
            fW = np.array([eval_one(W[i]) for i in range(n_puffins)])
            fY = np.array([eval_one(Y[i]) for i in range(n_puffins)])
            fZ = np.array([eval_one(Z[i]) for i in range(n_puffins)])
            n_evals += 3 * n_puffins

            # Merge W ∪ Y ∪ Z, sort, take top N — Eqs.(14)-(16)
            pool_X = np.vstack([W, Y, Z])
            pool_f = np.concatenate([fW, fY, fZ])
            top_N = np.argsort(pool_f)[:n_puffins]
            X_new = pool_X[top_N]
            f_new = pool_f[top_N]

        # ── Population replacement (fixed: full replacement) ──
        # X_new and f_new are already the top-N candidates in
        # sorted order. Their indices do NOT correspond to the
        # old population indices, so pairwise replacement would be
        # incorrect. Replace the entire population.
        X = X_new.copy()
        fitness = f_new.copy()

        # Update global best
        g_idx = int(np.argmin(fitness))
        if fitness[g_idx] < Gbest_fit:
            Gbest = X[g_idx].copy()
            Gbest_fit = float(fitness[g_idx])

        history.append(Gbest_fit)
        B_log.append(B)
        if record_diversity:
            diversity.append(_swarm_diversity(X))

        if verbose and (t + 1) % 10 == 0:
            div_str = (f"div={diversity[-1]:>6.2f}  "
                       if record_diversity else "")
            print(f"  iter {t+1:>3}/{T} | "
                  f"B={B:.3f} ({phase_log[-1]:>7}) | {div_str}"
                  f"best = ${Gbest_fit:>14,.2f}")

    runtime = time.time() - t_start

    # ── Extract best solution with full metrics ──────────────
    Gbest_int = np.round(Gbest).astype(int)
    _, best_metrics = evaluate_system(
        Gbest_int, site_name,
        LPSP_target, REP_target, return_full=True)
    n_evals += 1

    # Phase ratio (exploration vs. exploitation balance)
    n_explore = phase_log.count('explore')
    n_exploit = phase_log.count('exploit')

    return {
        # Identification
        "site": site_name,
        "algorithm": "APO",
        "seed": seed,
        # Solution
        "x_best": Gbest_int,
        "fitness": Gbest_fit,
        "metrics": best_metrics,
        # Constraint targets
        "LPSP_target": LPSP_target,
        "REP_target": REP_target,
        # Performance tracking (Q1 metadata)
        "history": np.array(history),
        "B_log": np.array(B_log),
        "phase_log": phase_log,
        "n_explore": n_explore,
        "n_exploit": n_exploit,
        "diversity": (np.array(diversity)
                     if record_diversity else None),
        "n_func_evals": n_evals,
        "runtime_sec": runtime,
        # Algorithm settings
        "settings": {
            "n_puffins": n_puffins,
            "n_iter": n_iter,
            "F": F,
            "C": C,
            "beta_levy": beta_levy,
        },
    }


# Note: _swarm_diversity() is defined in Cell 9a (PSO).
# Reused here for consistent diversity metrics across all algorithms.


# ── Verification ──────────────────────────────────────────────






# Cell 9d: Hybrid APO-PSO Optimization
# ============================================================
# Ref: Said, M., Anwar, T., El-Rifaie, A.M., et al. (2026).
#      "Performance of a Newly Developed Hybrid APO-PSO
#       Metaheuristic for Monitoring of Intelligent Transformer."
#      Machines, 14(2), 185.
#      DOI: 10.3390/machines14020185
#
# Component algorithms cited:
#   APO  : Wang, W., Tian, W., Xu, D., & Zang, H. (2024).
#          Advances in Engineering Software, 195, 103694.
#   PSO  : Kennedy, J. & Eberhart, R. (1995). IEEE ICNN.
#
# ── EXACT EQUATIONS (Said et al. 2026) ───────────────────────
#
# APO foraging update — Eq.(32)/(36):
#   T_i^APO(t+1) = T_i(t) + r * (P^best - T_i(t))
#   r ∈ (0,1) random SCALAR  ← paper page 10, direct quote
#
# PSO velocity update — Eq.(33):
#   v_i(t+1) = w * v_i(t)
#            + c1 * r1 * (P_i^best - T_i(t))
#            + c2 * r2 * (P^best   - T_i(t))
#   r1, r2 ∈ [0,1] scalars  ← paper page 11
#
# PSO position update — Eq.(34) / Eq.(37):
#   T_i^PSO(t+1) = T_i(t) + v_i(t+1)
#
# Time-dependent behavioral weight — Eq.(35):
#   λ(t) = exp(-t / T_max)
#   At t=0   : λ = 1.0   → hybrid is fully PSO
#   At t=T   : λ ≈ 0.368 → hybrid is ~63% APO, ~37% PSO
#
# ⚠️ Note on paper inconsistency:
#   Said et al. (2026) text describes APO-early/PSO-late
#   exploration→exploitation behavior, but the literal formula
#   λ = exp(-t/T_max) produces PSO-early/blend-late behavior.
#   We implement the FORMULA as stated for source fidelity.
#   The text–formula contradiction is acknowledged in the
#   manuscript Methods section.
#
# Hybrid update — Eq.(38) / Eq.(39):
#   T_i(t+1) = λ(t) * T_i^PSO(t+1) + (1 - λ(t)) * T_i^APO(t+1)
#
# Algorithm 1 (page 13) structure:
#   - Personal best updated INSIDE agent loop (line 21-23)
#   - Global best updated OUTSIDE agent loop, AFTER all agents
#     processed (line 26) — synchronous PSO
#
# Parameters (Said et al. 2026, Table 1, page 15):
#   w = 0.7, c1 = 1.5, c2 = 1.5, P = 100, T_max = 100
#   Note: paper uses P=100; we use 30 for compute consistency
#         with Cell 9a (PSO). Disclosed in manuscript.
#
# Implementation safeguards (not in source, disclosed):
#   - Boundary clipping  : positions clipped to [LB, UB]
#                         (required for integer-count problem)
#   - Velocity clamping  : v ∈ [-v_max, v_max], v_max=0.2×range
#                         (Eberhart & Shi 2000, standard PSO)
#   - Integer rounding   : np.round().astype(int)
#                         (decision variables are component counts)
#   - Non-finite guard   : replace inf/nan fitness with 1e12
# ============================================================

import numpy as np
import time


def apopso_optimize(site_name,
                    LPSP_target = 0.05,
                    REP_target  = 0.5,
                    n_agents    = 30,
                    n_iter      = 100,
                    w           = 0.7,    # PSO inertia, Said (2026) Table 1
                    c1          = 1.5,    # PSO cognitive, Said (2026) Table 1
                    c2          = 1.5,    # PSO social, Said (2026) Table 1
                    v_max_frac  = 0.2,    # safeguard, Eberhart & Shi (2000)
                    seed        = 42,
                    verbose     = True,
                    record_diversity = True):
    """
    Hybrid APO-PSO Optimization for HRES sizing.

    Implements Algorithm 1 of Said et al. (2026), Eqs.(32)-(39),
    with paper-literal choices: r and r1, r2 are scalars (page 10–11);
    global best updated synchronously outside agent loop (line 26).
    Implementation safeguards (boundary clipping, velocity clamping,
    integer rounding) added for the discrete integer-count problem.

    Parameters
    ----------
    site_name        : str   — site key in all_site_data
    LPSP_target      : float — reliability constraint, Eq.(37)
    REP_target       : float — renewable portion constraint, Eq.(39)
    n_agents         : int   — population size P
    n_iter           : int   — maximum iterations T_max
    w, c1, c2        : float — PSO coefficients (Said 2026 Table 1)
    v_max_frac       : float — velocity clamp (Eberhart & Shi 2000)
    seed             : int   — RNG seed for reproducibility
    verbose          : bool  — print progress every 10 iterations
    record_diversity : bool  — track population spatial diversity

    Returns
    -------
    dict — same structure as Cell 9a (PSO) for consistent comparison.
    """
    # ── Reproducibility ──────────────────────────────────────
    rng       = np.random.default_rng(seed)
    n_dim     = len(LB)
    T_max     = n_iter
    v_max     = v_max_frac * (UB - LB)
    n_evals   = 0
    t_start   = time.time()

    # ── Initialize population (Algorithm 1, lines 1-2) ───────
    X = rng.uniform(LB, UB, size=(n_agents, n_dim))
    V = rng.uniform(-v_max, v_max, size=(n_agents, n_dim))

    # Evaluate initial fitness (Algorithm 1, line 3)
    fitness = np.array([
        evaluate_system(np.round(X[i]).astype(int),
                        site_name, LPSP_target, REP_target)
        for i in range(n_agents)
    ])
    fitness = np.where(np.isfinite(fitness), fitness, 1e12)
    n_evals += n_agents

    # Personal best (Algorithm 1, line 4)
    Pbest     = X.copy()
    Pbest_fit = fitness.copy()

    # Global best (Algorithm 1, line 5)
    g_idx     = int(np.argmin(Pbest_fit))
    Gbest     = Pbest[g_idx].copy()
    Gbest_fit = float(Pbest_fit[g_idx])

    # ── Tracking ──────────────────────────────────────────────
    history    = [Gbest_fit]
    diversity  = [_swarm_diversity(X)] if record_diversity else None
    lambda_log = [1.0]   # λ(0) = exp(0) = 1

    # ── Main loop (Algorithm 1, line 6) ──────────────────────
    for t in range(T_max):

        # Behavioral weight — Eq.(35)
        # λ(t) = exp(-t / T_max)
        lam = float(np.exp(-t / T_max))

        # Inner loop over agents (Algorithm 1, line 9)
        for i in range(n_agents):

            # ── PSO velocity update — Eq.(33) ────────────────
            # r1, r2 are SCALARS per Said (2026) page 11
            r1 = rng.random()
            r2 = rng.random()

            V[i] = (w * V[i]
                    + c1 * r1 * (Pbest[i] - X[i])
                    + c2 * r2 * (Gbest    - X[i]))

            # Velocity clamping (safeguard, Eberhart & Shi 2000)
            V[i] = np.clip(V[i], -v_max, v_max)

            # ── PSO candidate — Eq.(34)/(37) ─────────────────
            T_PSO = X[i] + V[i]
            T_PSO = np.clip(T_PSO, LB, UB)

            # ── APO attraction update — Eq.(32)/(36) ─────────
            # r is a SCALAR per Said (2026) page 10
            r = rng.random()
            T_APO = X[i] + r * (Gbest - X[i])
            T_APO = np.clip(T_APO, LB, UB)

            # ── Hybrid update — Eq.(38)/(39) ─────────────────
            # T_i(t+1) = λ * T_PSO + (1 - λ) * T_APO
            # (no extra clip needed; convex combination of two
            #  bounded vectors is automatically within bounds)
            X_new = lam * T_PSO + (1.0 - lam) * T_APO

            # Evaluate fitness (Algorithm 1, line 20)
            f_new = evaluate_system(
                np.round(X_new).astype(int),
                site_name, LPSP_target, REP_target)
            if not np.isfinite(f_new):
                f_new = 1e12
            n_evals += 1

            # Update position
            X[i]       = X_new
            fitness[i] = f_new

            # ── Personal-best update (Algorithm 1, lines 21-23)
            if f_new < Pbest_fit[i]:
                Pbest[i]     = X_new.copy()
                Pbest_fit[i] = f_new

        # ── Global-best update (Algorithm 1, line 26) ────────
        # OUTSIDE agent loop — synchronous PSO per paper
        g_idx = int(np.argmin(Pbest_fit))
        if Pbest_fit[g_idx] < Gbest_fit:
            Gbest     = Pbest[g_idx].copy()
            Gbest_fit = float(Pbest_fit[g_idx])

        history.append(Gbest_fit)
        lambda_log.append(lam)
        if record_diversity:
            diversity.append(_swarm_diversity(X))

        if verbose and (t + 1) % 10 == 0:
            div_str = (f"div={diversity[-1]:>6.2f}  "
                       if record_diversity else "")
            print(f"  iter {t+1:>3}/{T_max} | "
                  f"λ={lam:.3f} | {div_str}"
                  f"best = ${Gbest_fit:>14,.2f}")

    runtime = time.time() - t_start

    # ── Extract best solution with full metrics ──────────────
    Gbest_int = np.round(Gbest).astype(int)
    _, best_metrics = evaluate_system(
        Gbest_int, site_name,
        LPSP_target, REP_target, return_full=True)
    n_evals += 1

    return {
        # Identification
        "site":         site_name,
        "algorithm":    "APO-PSO",
        "seed":         seed,
        # Solution
        "x_best":       Gbest_int,
        "fitness":      Gbest_fit,
        "metrics":      best_metrics,
        # Constraint targets
        "LPSP_target":  LPSP_target,
        "REP_target":   REP_target,
        # Performance tracking (Q1 metadata, matches Cell 9a)
        "history":      np.array(history),
        "lambda_log":   np.array(lambda_log),
        "diversity":    (np.array(diversity)
                         if record_diversity else None),
        "n_func_evals": n_evals,
        "runtime_sec":  runtime,
        # Algorithm settings (reproducibility)
        "settings": {
            "n_agents":   n_agents,
            "n_iter":     n_iter,
            "w":          w,
            "c1":         c1,
            "c2":         c2,
            "v_max_frac": v_max_frac,
        },
    }


# Note: _swarm_diversity() is already defined in Cell 9a (PSO).
# Reuse the same helper for consistent diversity metrics across
# all algorithms in the benchmark.


# ── Verification ──────────────────────────────────────────────






# Cell 9e: Golden Jackal Optimization (GJO)
# ============================================================
# Ref: Chopra, N., & Ansari, M. M. (2022).
#      "Golden jackal optimization: A novel nature-inspired
#       optimizer for engineering applications."
#      Expert Systems With Applications, 198, 116924.
#      DOI: 10.1016/j.eswa.2022.116924
#
# ── EXACT EQUATIONS (Chopra & Ansari 2022) ───────────────────
#
# Population initialization — Eq.(1):
#   Y0 = Ymin + rand * (Ymax − Ymin)
#   rand ∈ (0,1) uniform random vector  [paper page 4]
#
# Population matrix — Eq.(2):
#   Prey = [Y_{i,j}]  for i = 1..n preys, j = 1..d dimensions
#
# Fitness matrix — Eq.(3):
#   F_OA[i] = f(Y_{i,1}, ..., Y_{i,d})
#
# Social hierarchy (page 4, direct quote):
#   "The fittest one is called Male Jackal and the second
#    fittest is called Female Jackal."
#   → Y_M  = best prey (Male jackal)
#   → Y_FM = second-best prey (Female jackal)
#   Re-identified at the START of each iteration (Fig. 4).
#
# ── EXPLORATION STAGE (searching), used when |E| ≥ 1 ──
#
# Male jackal update — Eq.(4):
#   Y1(t) = Y_M(t) − E · |Y_M(t) − rl · Prey(t)|
#
# Female jackal update — Eq.(5):
#   Y2(t) = Y_FM(t) − E · |Y_FM(t) − rl · Prey(t)|
#
# Note: "Prey(t)" in Eqs.(4)–(5) means the CURRENT candidate
# being updated (i.e., X_i(t) in standard notation), not a
# separate prey location. Y_M / Y_FM are the leaders.
# (Paper page 6, variable definitions.)
#
# ── EXPLOITATION STAGE (enclosing/pouncing), used when |E| < 1 ──
#
# Male jackal update — Eq.(12):
#   Y1(t) = Y_M(t) − E · |rl · Y_M(t) − Prey(t)|
#
# Female jackal update — Eq.(13):
#   Y2(t) = Y_FM(t) − E · |rl · Y_FM(t) − Prey(t)|
#
# Structural difference: rl multiplies the LEADER (Y_M, Y_FM)
# in exploitation vs. multiplying Prey(t) in exploration.
#
# ── FINAL POSITION UPDATE — Eq.(11) ──
#
#   Y(t+1) = ( Y1(t) + Y2(t) ) / 2
#
# Same averaging rule for both phases.
#
# ── EVADING ENERGY E ──
#
# Eq.(6):   E  = E1 · E0
# Eq.(7):   E0 = 2 · r − 1     where r ∈ (0,1) scalar
# Eq.(8):   E1 = c1 · (1 − t/T)    c1 = 1.5 constant
#
# E0 ∈ [−1, 1]; E1 linearly decays from 1.5 to 0 over t ∈ [0, T]
# E ∈ [−1.5, 1.5] at t=0, → 0 as t → T
#
# Phase switching (pseudo-code Fig. 4, page 3):
#   if |E| ≥ 1 : exploration  (Eqs. 4, 5, 11)
#   if |E| < 1 : exploitation (Eqs. 12, 13, 11)
#
# ── LEVY FLIGHT rl ──
#
# Eq.(9):   rl = 0.05 · LF(y)
#
# Eq.(10):  LF(y) = 0.01 · (μ · σ) / |v|^(1/β)
#
#           σ = [ Γ(1+β) · sin(πβ/2) /
#                 ( Γ((1+β)/2) · β · 2^((β−1)/2) ) ]^(1/β)
#
#   β = 1.5 (paper page 6, default constant)
#
# ⚠️ Inconsistency disclosed in manuscript:
#   Paper text says "u, v are random values inside (0,1)" but
#   the Mantegna (1994) algorithm cited via Faramarzi et al.
#   (2020, ref for Eq. 9) requires μ ~ N(0, σ²), v ~ N(0, 1).
#   We follow the canonical Mantegna formulation (normal
#   samples) — same disclosure pattern as Cell 9c (APO).
#
# ── ALGORITHM (Fig. 4, page 3) — VERBATIM STRUCTURE ──
#
#   Initialize prey population Y_i (i = 1..N) via Eq.(1)
#   while t < T:
#     1. Calculate fitness of all preys
#     2. Y_M  = best prey
#     3. Y_FM = second-best prey
#     4. for each prey i = 1..N:
#          a. Update E via Eqs.(6)-(8)        [per-prey draw]
#          b. Update rl via Eqs.(9)-(10)      [per-prey draw]
#          c. if |E| ≥ 1:  update via Eqs.(4),(5),(11)
#             else:        update via Eqs.(12),(13),(11)
#     5. t = t + 1
#   return Y_M
#
# Key structural notes (different from APO Cell 9c):
#   - E and rl are re-drawn PER PREY PER ITERATION
#     (update lines are inside the for-each-prey loop)
#   - Branching is PER-PREY, not per-iteration as in APO
#     (each prey decides explore/exploit on its own |E|)
#   - Output is Y_M (Male jackal) at termination
#
# ── PARAMETERS (paper Section 3, page 9) ──
#
#   n  = 30    (population)
#   T  = 200   (iterations) — paper benchmark
#   c1 = 1.5   (Eq. 8 constant; Table 6 sensitivity)
#   β  = 1.5   (Lévy stability index, Eq. 10)
#   30 independent runs per benchmark function
#
#   Note: paper benchmarks use 30×200; we use 30×100 for
#   compute consistency with Cells 9a–9d. Disclosed.
#
# ── IMPLEMENTATION SAFEGUARDS (consistent with 9a–9d) ──
#
#   - Boundary clipping  : positions clipped to [LB, UB]
#                          (paper does NOT specify boundary
#                          handling for box bounds; required
#                          for integer-count problem)
#   - Integer rounding   : np.round().astype(int) on evaluation
#                          (decision variables ∈ ℤ⁺)
#   - Non-finite guard   : replace inf/nan fitness with 1e12
#   - Lévy formulation   : Mantegna with μ, v ~ N (canonical,
#                          per Faramarzi 2020 reference)
#   - Phase threshold    : |E| ≥ 1 per pseudo-code Fig. 4
#                          (text on page 7 says "|E| > 1" —
#                          probability-zero difference; we
#                          follow the pseudo-code)
#   - Leader elitism     : Male/Female pair pooled with stored
#                          leaders before re-identifying top-2.
#                          Paper pseudo-code does NOT specify
#                          elitism, but without it the leader
#                          pair can degrade. Same pattern as
#                          Cell 9b (GWO α/β/δ pool-and-sort).
# ============================================================

import numpy as np
import time
from math import gamma, pi, sin


def gjo_optimize(site_name,
                 LPSP_target = 0.05,
                 REP_target  = 0.5,
                 n_jackals   = 30,
                 n_iter      = 100,
                 c1          = 1.5,    # E1 constant, paper Eq.(8)
                 beta_levy   = 1.5,    # Mantegna β, paper Eq.(10)
                 seed        = 42,
                 verbose     = True,
                 record_diversity = True):
    """
    Golden Jackal Optimization for HRES sizing.

    Implements the GJO algorithm of Chopra & Ansari (2022),
    Eqs.(1)-(13), with implementation safeguards consistent
    with Cells 9a (PSO), 9b (GWO), 9c (APO), and 9d (APO-PSO).

    Lévy flight uses the Mantegna (1994) algorithm with β = 1.5,
    matching the Faramarzi et al. (2020) Marine Predator Algorithm
    reference cited by the paper for Eq.(9).

    Parameters
    ----------
    site_name        : str   — site key in all_site_data
    LPSP_target      : float — reliability constraint
    REP_target       : float — renewable portion constraint
    n_jackals        : int   — population size N (preys)
    n_iter           : int   — maximum iterations T
    c1               : float — E1 decay constant (paper: 1.5)
    beta_levy        : float — Mantegna stability index (1.5)
    seed             : int   — RNG seed for reproducibility
    verbose          : bool  — print progress every 10 iterations
    record_diversity : bool  — track population spatial diversity

    Returns
    -------
    dict — same structure as Cells 9a–9d for consistent comparison.
    """
    # ── Reproducibility ──────────────────────────────────────
    rng     = np.random.default_rng(seed)
    n_dim   = len(LB)
    T       = n_iter
    n_evals = 0
    t_start = time.time()

    # Mantegna σ_u for Lévy flight (constant; depends only on β)
    sigma_u = (gamma(1 + beta_levy) * sin(pi * beta_levy / 2) /
               (gamma((1 + beta_levy) / 2) *
                beta_levy * 2 ** ((beta_levy - 1) / 2))) ** (1 / beta_levy)

    def levy(d):
        """
        rl per Eq.(9): rl = 0.05 * LF(y)
        LF(y) per Eq.(10): 0.01 * (μ * σ) / |v|^(1/β)
        Returns vector of length d.
        """
        u = rng.normal(0.0, sigma_u, size=d)
        v = rng.normal(0.0, 1.0,     size=d)
        LF = 0.01 * u / (np.abs(v) ** (1.0 / beta_levy))
        return 0.05 * LF

    def eval_one(x):
        """Evaluate one candidate solution with safeguards."""
        f = evaluate_system(np.round(x).astype(int),
                            site_name, LPSP_target, REP_target)
        if not np.isfinite(f):
            f = 1e12
        return f

    # ── Initialize prey population — Eq.(1) ──────────────────
    Y = rng.uniform(LB, UB, size=(n_jackals, n_dim))
    fitness = np.array([eval_one(Y[i]) for i in range(n_jackals)])
    n_evals += n_jackals

    # Identify Male & Female jackals (best, second-best)
    sorted_idx = np.argsort(fitness)
    Y_M  = Y[sorted_idx[0]].copy()       # Male  (best)
    Y_FM = Y[sorted_idx[1]].copy()       # Female (2nd best)
    f_M  = float(fitness[sorted_idx[0]])
    f_FM = float(fitness[sorted_idx[1]])

    # Best so far (Y_M, by definition of pseudo-code "return Y1")
    Gbest     = Y_M.copy()
    Gbest_fit = f_M

    # ── Tracking ──────────────────────────────────────────────
    history    = [Gbest_fit]
    E1_log     = [c1 * 1.0]              # E1 at t=0
    phase_log  = []                      # (n_explore, n_exploit) per iter
    diversity  = [_swarm_diversity(Y)] if record_diversity else None

    # ── Main loop (Fig. 4, page 3) ───────────────────────────
    for t in range(T):

        # E1 decay — Eq.(8): E1 = c1 * (1 - t/T)
        # (logged once per iteration; E0 is per-prey)
        E1 = c1 * (1.0 - t / T)

        # Per-prey phase counter for this iteration
        n_explore_this_iter = 0
        n_exploit_this_iter = 0

        # Inner loop over preys (Fig. 4, "for each prey")
        for i in range(n_jackals):

            # ── Update E via Eqs.(6)-(8) — PER PREY ─────────
            r  = rng.random()                 # scalar, Eq.(7)
            E0 = 2.0 * r - 1.0                # Eq.(7)
            E  = E1 * E0                      # Eq.(6)

            # ── Update rl via Eqs.(9)-(10) — PER PREY ───────
            rl = levy(n_dim)                  # vector length n_dim

            # ── Phase branching per |E| (Fig. 4) ────────────
            if abs(E) >= 1.0:
                # EXPLORATION — Eqs.(4), (5)
                # Y1 = Y_M  - E * |Y_M  - rl * Prey|
                # Y2 = Y_FM - E * |Y_FM - rl * Prey|
                Y1 = Y_M  - E * np.abs(Y_M  - rl * Y[i])
                Y2 = Y_FM - E * np.abs(Y_FM - rl * Y[i])
                n_explore_this_iter += 1
            else:
                # EXPLOITATION — Eqs.(12), (13)
                # Y1 = Y_M  - E * |rl * Y_M  - Prey|
                # Y2 = Y_FM - E * |rl * Y_FM - Prey|
                Y1 = Y_M  - E * np.abs(rl * Y_M  - Y[i])
                Y2 = Y_FM - E * np.abs(rl * Y_FM - Y[i])
                n_exploit_this_iter += 1

            # Final position — Eq.(11): mean of Y1 and Y2
            Y_new = (Y1 + Y2) / 2.0

            # Boundary clipping (safeguard, not in source)
            Y_new = np.clip(Y_new, LB, UB)

            # Update prey position (per pseudo-code: unconditional;
            # source has no greedy replacement step)
            Y[i] = Y_new

        # ── Re-evaluate all preys (top of next iter in pseudo-code:
        #    "Calculate the fitness values of preys") ─────────
        fitness = np.array([eval_one(Y[i]) for i in range(n_jackals)])
        n_evals += n_jackals

        # ── Update Male & Female jackals ────────────────────
        # Pool current population with stored leaders, take top 2.
        # Provides elitism (paper pseudo-code does not specify it,
        # but without it the leader pair can degrade between
        # iterations). Same pattern as Cell 9b (GWO leader pool).
        pool_X = np.vstack([Y, Y_M[np.newaxis, :], Y_FM[np.newaxis, :]])
        pool_f = np.concatenate([fitness, [f_M, f_FM]])
        top2   = np.argsort(pool_f)[:2]

        Y_M  = pool_X[top2[0]].copy()
        Y_FM = pool_X[top2[1]].copy()
        f_M  = float(pool_f[top2[0]])
        f_FM = float(pool_f[top2[1]])

        # Track global best (= Y_M by pseudo-code "return Y1")
        if f_M < Gbest_fit:
            Gbest     = Y_M.copy()
            Gbest_fit = f_M

        history.append(Gbest_fit)
        E1_log.append(E1)
        phase_log.append((n_explore_this_iter, n_exploit_this_iter))
        if record_diversity:
            diversity.append(_swarm_diversity(Y))

        if verbose and (t + 1) % 10 == 0:
            div_str = (f"div={diversity[-1]:>6.2f}  "
                       if record_diversity else "")
            pct_explore = 100.0 * n_explore_this_iter / n_jackals
            print(f"  iter {t+1:>3}/{T} | "
                  f"E1={E1:.3f} | exp={pct_explore:>5.1f}% | "
                  f"{div_str}best = ${Gbest_fit:>14,.2f}")

    runtime = time.time() - t_start

    # ── Extract best solution with full metrics ──────────────
    Gbest_int = np.round(Gbest).astype(int)
    _, best_metrics = evaluate_system(
        Gbest_int, site_name,
        LPSP_target, REP_target, return_full=True)
    n_evals += 1

    # Aggregate phase totals
    n_explore_total = sum(p[0] for p in phase_log)
    n_exploit_total = sum(p[1] for p in phase_log)
    total_branches  = n_explore_total + n_exploit_total

    return {
        # Identification
        "site":         site_name,
        "algorithm":    "GJO",
        "seed":         seed,
        # Solution
        "x_best":       Gbest_int,
        "fitness":      Gbest_fit,
        "metrics":      best_metrics,
        # Constraint targets
        "LPSP_target":  LPSP_target,
        "REP_target":   REP_target,
        # Performance tracking (Q1 metadata)
        "history":      np.array(history),
        "E1_log":       np.array(E1_log),
        "phase_log":    phase_log,         # list of (n_exp, n_expl) per iter
        "n_explore":    n_explore_total,   # total prey-branch events
        "n_exploit":    n_exploit_total,
        "diversity":    (np.array(diversity)
                         if record_diversity else None),
        "n_func_evals": n_evals,
        "runtime_sec":  runtime,
        # Algorithm settings (reproducibility)
        "settings": {
            "n_jackals": n_jackals,
            "n_iter":    n_iter,
            "c1":        c1,
            "beta_levy": beta_levy,
        },
    }


# Note: _swarm_diversity() is defined in Cell 9a (PSO).
# Reused here for consistent diversity metrics across all algorithms.


# ── Verification ──────────────────────────────────────────────







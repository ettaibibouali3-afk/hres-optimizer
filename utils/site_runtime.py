"""
utils/site_runtime.py
=====================

Prepares a site (preset or custom) so that evaluate_system() can use it.

The notebook code expects three global dicts populated for each site:
    core.all_site_data[site_name]      -> DataFrame with GHI, temp, wind_speed
    core.PV_UNIT_PROFILES[site_name]   -> per-panel hourly power array
    core.LOAD_PROFILES[site_name]      -> 8760-element load array

For custom locations entered in the Streamlit UI, this module fetches PVGIS
data on demand, runs the slow PV unit precompute once, and registers the
site in the same global dicts.

Also provides registration of custom sites in core.STUDY_SITES so that
get_economic_factors() can find user-supplied economic parameters.
"""

import time
import streamlit as st
import core


# ────────────────────────────────────────────────────────────────────
# Climate zone detection from coordinates (simple lat/Köppen heuristic)
# ────────────────────────────────────────────────────────────────────
def detect_climate_zone(lat: float, lon: float) -> str:
    """
    Returns a coarse climate zone label from coordinates.

    This is a simple latitude-based heuristic; for a more rigorous
    classification, replace with a Köppen-Geiger raster lookup
    (Beck et al., 2018).
    """
    abs_lat = abs(lat)
    if abs_lat < 15:
        return "Tropical"
    if abs_lat < 30:
        return "Arid / Subtropical"
    if abs_lat < 45:
        return "Temperate / Mediterranean"
    if abs_lat < 60:
        return "Continental"
    return "Polar"


# ────────────────────────────────────────────────────────────────────
# Site preparation
# ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _cached_pvgis_fetch(lat: float, lon: float, label: str):
    """
    Fetch PVGIS TMY data with caching. Cached for 24 hours per (lat, lon).
    """
    return core.fetch_pvgis_data(lat, lon, label)


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _cached_pv_unit_profile(_df, label: str):
    """
    Precompute per-panel PV power. Slow: ~5 seconds per site (Brent loop).
    Cached on (DataFrame hash, label) to avoid repeat computation.
    """
    return core.precompute_pv_unit(_df)


def prepare_site(
    site_name: str,
    lat: float,
    lon: float,
    fuel_price_USD_per_L: float,
    ir_nom: float,
    fr: float,
    avg_load_kW: float = 36.0,
    region: str = "Custom",
    climate: str = None,
    description: str = "",
):
    """
    Register a (preset or custom) site so it can be optimized.

    Populates:
        core.STUDY_SITES[site_name]      with metadata + economics
        core.all_site_data[site_name]    with PVGIS DataFrame
        core.PV_UNIT_PROFILES[site_name] with per-panel hourly profile
        core.LOAD_PROFILES[site_name]    with 8760 load array

    Parameters
    ----------
    site_name : str  — display label (also dict key)
    lat, lon  : float
    fuel_price_USD_per_L : float
    ir_nom    : float (decimal, e.g. 0.0225 for 2.25%)
    fr        : float (decimal, e.g. 0.0172 for 1.720%)
    avg_load_kW : float
    region    : str
    climate   : str  — auto-detected if None
    description : str

    Returns
    -------
    dict — info subset of core.STUDY_SITES[site_name]
    """
    if climate is None:
        climate = detect_climate_zone(lat, lon)

    # 1) Register site metadata + economics
    core.STUDY_SITES[site_name] = {
        "country": region,
        "lat": lat,
        "lon": lon,
        "region": region,
        "climate": climate,
        "description": description,
        "fuel_price_USD_per_L": fuel_price_USD_per_L,
        "ir_nom": ir_nom,
        "fr": fr,
    }

    # 2) Fetch PVGIS data (cached)
    if site_name not in core.all_site_data:
        df = _cached_pvgis_fetch(lat, lon, site_name)
        if df is None:
            raise RuntimeError(
                f"Could not fetch PVGIS TMY data for ({lat:.3f}, {lon:.3f}). "
                "Check internet connection or coordinates."
            )
        core.all_site_data[site_name] = df

    # 3) Precompute PV unit profile (cached)
    if site_name not in core.PV_UNIT_PROFILES:
        df = core.all_site_data[site_name]
        core.PV_UNIT_PROFILES[site_name] = _cached_pv_unit_profile(df, site_name)

    # 4) Generate load profile (fast — no cache needed)
    if site_name not in core.LOAD_PROFILES:
        hem = core.site_hemisphere(lat)
        core.LOAD_PROFILES[site_name] = core.generate_load_profile(
            avg_load_kW=avg_load_kW,
            hemisphere=hem,
            seed=42,
        )

    return core.STUDY_SITES[site_name]


def reset_load_profile(site_name: str, avg_load_kW: float, lat: float):
    """
    Regenerate the load profile for a site (e.g. when user changes avg load).
    """
    hem = core.site_hemisphere(lat)
    core.LOAD_PROFILES[site_name] = core.generate_load_profile(
        avg_load_kW=avg_load_kW,
        hemisphere=hem,
        seed=42,
    )
    # Invalidate diesel baseline cache (depends on load)
    core._DIESEL_BASELINE_CACHE.pop(site_name, None)

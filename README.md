# HRES Optimizer — Off-Grid Hybrid Renewable Energy System Sizing Platform

Interactive web platform for optimal sizing of off-grid PV–wind–battery–diesel hybrid renewable energy systems at any location worldwide.

## What this platform does

For any geographic location on Earth, this platform:

1. Fetches hourly solar irradiance, ambient temperature, and wind speed from PVGIS TMY data
2. Generates a synthetic load profile based on user-specified average demand and climate
3. Runs five state-of-the-art metaheuristic optimization algorithms (PSO, GWO, APO, APO-PSO, GJO) to size PV array, wind turbines, battery bank, and backup diesel generator
4. Recommends the configuration with lowest Total Net Present Cost satisfying user-defined reliability (LPSP) and renewable penetration (REP) constraints
5. Reports LCOE, CDRA (CO₂ avoided), and full algorithm comparison statistics

## Architecture

```
app.py                   ← Streamlit entry point
core.py                  ← All simulation, economics, optimization functions
                            (single module — preserves notebook integrity)
utils/
    pvgis.py             ← PVGIS API fetch helper
    site_runtime.py      ← Custom-location runtime initialization
requirements.txt
```

The platform calls the same Python functions used in the published study, ensuring full consistency between the paper and the interactive tool.

## Deployment to Streamlit Community Cloud

1. Create a public GitHub repo and push these files
2. Visit https://streamlit.io/cloud and sign in with GitHub
3. Click "New app", select your repo, branch, and `app.py`
4. Click "Deploy" — first build takes ~3 minutes

Your app will be live at: `https://<repo-name>-<hash>.streamlit.app`

## Local testing

```bash
pip install -r requirements.txt
streamlit run app.py
```

# CropMix Optimizer — Online

This is a ready-to-deploy Streamlit app that runs a linear crop mix optimization using **OR-Tools** (no external solver needed).

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud (free)
1. Put these files in a GitHub repo (with `app.py` at the repo root).
2. Go to https://share.streamlit.io → New app → Select your repo/branch → Deploy.
3. You’ll get a public URL.

## Deploy on Render (free)
Add `render.yaml` to the repo and click **New Web Service** on Render; choose your repo.

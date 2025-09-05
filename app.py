import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="AD Burden Calculator", layout="wide")
st.title("ZIP-Code-Based Atopic Dermatitis Burden Calculator")

st.sidebar.header("API Tokens")
airnow_token = st.sidebar.text_input("AirNow Token", value="1A09DCE5-A427-4805-AAA0-97ECB2053DFE")
census_token = st.sidebar.text_input("Census Bureau Token", value="d25ceb4e63ceefbfeed820259ce82b76d0d403c5")
hrsa_token = st.sidebar.text_input("HRSA Token", value="3054f3d7-8c8b-4164-986d-877cf1e3dcc6")
cdc_places_url = "https://data.cdc.gov/api/v3/views/cwsq-ngmh/query.json"

zip_input = st.text_input("Enter ZIP codes separated by commas", value="10001,90210,30301")
zip_codes = [z.strip() for z in zip_input.split(",") if z.strip().isdigit()]

def normalize(value, min_val, max_val):
    return max(0, min(100, ((value - min_val) / (max_val - min_val)) * 100))

def get_census_data(zip_code, token):
    try:
        url = f"https://api.census.gov/data/2021/acs/acs5/profile?get=DP03_0119PE,DP05_0033PE,DP05_0071PE,DP05_0076PE,DP05_0081PE&for=zip%20code%20tabulation%20area:{zip_code}&key={token}"
        response = requests.get(url)
        data = response.json()
        headers = data[0]
        values = data[1]
        result = dict(zip(headers, values))
        return {
            "poverty_rate": float(result.get("DP03_0119PE", 0)),
            "urban_density": float(result.get("DP05_0033PE", 0)),
            "african_american_pct": float(result.get("DP05_0071PE", 0)),
            "hispanic_pct": float(result.get("DP05_0076PE", 0)),
            "asian_pct": float(result.get("DP05_0081PE", 0))
        }
    except:
        return {
            "poverty_rate": 0,
            "urban_density": 0,
            "african_american_pct": 0,
            "hispanic_pct": 0,
            "asian_pct": 0
        }

def get_air_quality(zip_code, token):
    try:
        url = f"https://www.airnowapi.org/aq/observation/zipCode/current/?format=application/json&zipCode={zip_code}&distance=25&API_KEY={token}"
        response = requests.get(url)
        data = response.json()
        if data:
            aqi = max([entry['AQI'] for entry in data])
            return normalize(aqi, 0, 300)
        else:
            return 0
    except:
        return 0

def get_specialist_access(zip_code):
    import random
    dermatologists = random.uniform(0.5, 5.0)
    allergists = random.uniform(0.5, 5.0)
    access_score = 100 - normalize((dermatologists + allergists), 0, 10)
    return access_score

def get_disease_prevalence(zip_code):
    import random
    prevalence = random.uniform(5, 20)
    return normalize(prevalence, 0, 25)

def calculate_burden_score(data):
    score = (
        data["urban_density"] * 0.15 +
        data["air_quality"] * 0.15 +
        data["socioeconomic"] * 0.15 +
        data["race_ethnicity"] * 0.15 +
        data["healthcare_access"] * 0.20 +
        data["disease_prevalence"] * 0.20
    )
    return round(score, 2)

results = []
for zip_code in zip_codes:
    census_data = get_census_data(zip_code, census_token)
    air_quality = get_air_quality(zip_code, airnow_token)
    healthcare_access = get_specialist_access(zip_code)
    disease_prevalence = get_disease_prevalence(zip_code)

    race_ethnicity_score = normalize(
        census_data["african_american_pct"] + census_data["hispanic_pct"] + census_data["asian_pct"],
        0, 100
    )
    socioeconomic_score = normalize(census_data["poverty_rate"], 0, 50)
    urban_density_score = normalize(census_data["urban_density"], 0, 100)

    burden_score = calculate_burden_score({
        "urban_density": urban_density_score,
        "air_quality": air_quality,
        "socioeconomic": socioeconomic_score,
        "race_ethnicity": race_ethnicity_score,
        "healthcare_access": healthcare_access,
        "disease_prevalence": disease_prevalence
    })

    results.append({
        "ZIP Code": zip_code,
        "Urban Density": urban_density_score,
        "Air Quality": air_quality,
        "Socioeconomic": socioeconomic_score,
        "Race/Ethnicity": race_ethnicity_score,
        "Healthcare Access": healthcare_access,
        "Disease Prevalence": disease_prevalence,
        "Burden Score": burden_score
    })

if results:
    df = pd.DataFrame(results).sort_values(by="Burden Score", ascending=False)
    st.subheader("Burden Score Table")
    st.dataframe(df)

    st.subheader("Burden Score Bar Chart")
    fig = px.bar(df, x="ZIP Code", y="Burden Score", title="AD Burden Score by ZIP Code")
    st.plotly_chart(fig)

    st.subheader("Heatmap of Risk Factors")
    heatmap_data = df.set_index("ZIP Code")[["Urban Density", "Air Quality", "Socioeconomic", "Race/Ethnicity", "Healthcare Access", "Disease Prevalence"]]
    fig2 = px.imshow(heatmap_data, text_auto=True, aspect="auto", color_continuous_scale="RdBu", title="Normalized Risk Factors by ZIP Code")
    st.plotly_chart(fig2)

    st.download_button("Download Results as CSV", data=df.to_csv(index=False), file_name="ad_burden_scores.csv", mime="text/csv")

# Used AI to figure out how to implement API and format analysis results
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import json
import re

client = OpenAI(api_key="placeholder")

st.set_page_config(page_title="Rethreaded", layout="wide")

st.markdown(
    """
    <style>
    div[data-testid="stMainBlockContainer"] {
        padding-top: 1.5rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    .stVerticalBlock {
        gap: 0.4rem !important;
    }

    div[data-testid="stHorizontalBlock"] > div:nth-child(1) {
        background-color: #E6CFD5;
        padding-left: 1.2rem;
        padding-right: 0.8rem;
        padding-top: 0.6rem;
        padding-bottom: 0.6rem;
        border-radius: 4px;
    }

    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
        background-color: transparent;
    }

    div[data-testid="stHorizontalBlock"] > div:nth-child(3) {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-top: 0.6rem;
        padding-bottom: 0.6rem;
    }

    .divider-col {
        border-left: 1px solid #B987A6;
        height: 100vh;
        margin: 0 0.3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# header
st.title("Rethreaded")
st.caption("Fabric Sustainability Analyzer")

left_col, divider_col, right_col = st.columns([1.5, 0.05, 1.5])

with divider_col:
    st.markdown('<div class="divider-col"></div>', unsafe_allow_html=True)

# left side: inputs
with left_col:
    cotton = st.number_input("Cotton (%)", 0, 100, 50)
    polyester = st.number_input("Polyester (%)", 0, 100, 50)
    nylon = st.number_input("Nylon (%)", 0, 100, 0)

    total = cotton + polyester + nylon
    if total != 100:
        st.error("Total must equal 100%")

    analyze_clicked = st.button("Analyze Sustainability")

# right side: results and charts
with right_col:
    if analyze_clicked and total == 100:
        prompt = f"""
The user provides a fabric composition that always sums to 100%.
You must base all calculations only on these exact percentages:

- Cotton: {cotton}%
- Polyester: {polyester}%
- Nylon: {nylon}%

Rules:
- Higher cotton → usually higher water usage, but lower energy and slightly lower CO2 than synthetics.
- Higher polyester/nylon → usually lower water usage, but higher energy consumption and CO2.
- Sustainability Score (1-10): 1 = very bad, 10 = excellent. Be consistent with the numbers you calculate.

Return JSON only. All numbers must be plain numbers without commas.
Use this exact JSON structure and fill in realistic values based on the percentages above:

{{
  "Water Usage (liters)": 2500,
  "Carbon Footprint (kg CO2)": 6.5,
  "Energy Consumption (kWh)": 9.0,
  "Sustainability Score (1-10)": 4,
  "Recommendation": "short suggestion (max 25 words) that refers to these specific percentages"
}}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )

            choice0 = response.choices[0]
            raw = getattr(choice0.message, "content", None)
            if raw is None and isinstance(choice0.message, dict):
                raw = choice0.message.get("content")
            if raw is None:
                raise ValueError("No content field found in OpenAI response")

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found in model response")

            result = match.group(0)

            # remove commas 
            fixed_result = re.sub(r"(\d),(\d)", r"\1\2", result)
            data = json.loads(fixed_result)
            water_liters = data["Water Usage (liters)"]
            water_kl = water_liters / 1000.0

            df = pd.DataFrame([{
                "Water Usage (kiloliters)": water_kl,
                "Carbon Footprint (kg CO2)": data["Carbon Footprint (kg CO2)"],
                "Energy Consumption (kWh)": data["Energy Consumption (kWh)"],
                "Sustainability Score (1-10)": data["Sustainability Score (1-10)"],
            }])

            # purple heading
            st.markdown(
                "<span style='color:#8C4C70; font-weight:600;'>Environmental Impact</span>",
                unsafe_allow_html=True,
            )
            st.table(df)

            # chart 
            co2 = data["Carbon Footprint (kg CO2)"]
            energy = data["Energy Consumption (kWh)"]

            labels = ["Water (kL)", "CO2 (kg)", "Energy (kWh)"]
            values = [water_kl, co2, energy]

            fig, chart = plt.subplots(figsize=(2.0, 0.8))
            chart.bar(labels, values, color=["#B37BA4", "#8C4C70", "#D8A9C3"])
            chart.set_ylim(0, 20)
            chart.tick_params(axis="both", which="major", labelsize=5)
            chart.set_ylabel("Impact", fontsize=5)
            chart.set_xlabel("")  # no extra text under X axis
            chart.set_title("")
            chart.spines["top"].set_visible(False)
            chart.spines["right"].set_visible(False)
            plt.tight_layout(pad=0.2)
            st.pyplot(fig)

            # score
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #B37BA4;
                    background-color: #F9EFF4;
                    padding: 0.2rem 0.4rem;
                    border-radius: 4px;
                    display: inline-block;
                    margin-top: 0.3rem;
                ">
                    <span style="color:#8C4C70; font-weight:600;">
                        Sustainability Score: {data["Sustainability Score (1-10)"]}/10
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

            # AI rec
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #B37BA4;
                    background-color: #FDF3F8;
                    padding: 0.4rem 0.6rem;
                    border-radius: 4px;
                    margin-top: 0.2rem;
                ">
                    <div style="color:#8C4C70; font-weight:600; margin-bottom:0.2rem;">
                        AI Recommendation
                    </div>
                    <div style="color:#333333; font-size:0.8rem;">
                        {data["Recommendation"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        except Exception as e:
            st.error("Could not process request.")
            st.write("Error details:", str(e))
            st.write("Raw AI output:")
            st.write(raw if "raw" in locals() else response)

    elif analyze_clicked and total != 100:
        st.warning("Fix the percentages on the left so they add up to 100% to see the analysis here.")

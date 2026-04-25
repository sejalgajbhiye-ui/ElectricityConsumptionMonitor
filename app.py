import pandas as pd
import plotly.express as px
import requests
import streamlit as st


CITY = "Pune"
PUNE_LATITUDE = 18.5204
PUNE_LONGITUDE = 73.8567
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
MSEDCL_SLABS = [
    {"from": 0, "to": 100, "rate": 3.44, "label": "0-100 units"},
    {"from": 101, "to": 300, "rate": 7.34, "label": "101-300 units"},
    {"from": 301, "to": 500, "rate": 10.26, "label": "301-500 units"},
    {"from": 501, "to": 1000, "rate": 11.31, "label": "501-1000 units"},
    {"from": 1001, "to": None, "rate": 12.50, "label": "Above 1000 units"},
]
ELECTRICITY_DUTY_RATE = 0.05


st.set_page_config(
    page_title="Electricity Consumption & Bill Prediction System",
    page_icon="⚡",
    layout="wide",
)


def calculate_bill(units):
    """Estimate Pune residential MSEDCL bill using progressive slabs."""
    remaining_units = max(units, 0)
    energy_charge = 0
    breakdown = []

    for slab in MSEDCL_SLABS:
        lower_limit = slab["from"]
        upper_limit = slab["to"]

        if upper_limit is None:
            slab_capacity = remaining_units
        else:
            slab_capacity = upper_limit - lower_limit + 1

        slab_units = min(remaining_units, slab_capacity)
        if slab_units <= 0:
            continue

        charge = slab_units * slab["rate"]
        energy_charge += charge
        breakdown.append(
            {
                "Slab": slab["label"],
                "Units": slab_units,
                "Rate": slab["rate"],
                "Amount": charge,
            }
        )
        remaining_units -= slab_units

        if remaining_units <= 0:
            break

    fixed_charge = get_fixed_charge(units)
    electricity_duty = energy_charge * ELECTRICITY_DUTY_RATE
    total_bill = energy_charge + fixed_charge + electricity_duty

    return {
        "energy_charge": energy_charge,
        "fixed_charge": fixed_charge,
        "electricity_duty": electricity_duty,
        "total_bill": total_bill,
        "breakdown": breakdown,
    }


def get_fixed_charge(units):
    """Estimate fixed charges based on monthly residential usage."""
    if units <= 100:
        return 95
    if units <= 300:
        return 120
    return 170


def predict_units(m1, m2, m3):
    """Predict base units from the last three months."""
    weighted = m1 * 0.2 + m2 * 0.3 + m3 * 0.5
    growth = ((m2 - m1) + (m3 - m2)) / 2
    trend = m3 + growth
    base_prediction = (weighted + trend) / 2

    return {
        "weighted": weighted,
        "growth": growth,
        "trend": trend,
        "base_prediction": base_prediction,
    }


def fetch_pune_forecast():
    """Fetch Pune's 7-day forecast from Open-Meteo. No API key is required."""
    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": PUNE_LATITUDE,
                "longitude": PUNE_LONGITUDE,
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "Asia/Kolkata",
                "forecast_days": 7,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        dates = data["daily"]["time"]
        max_temps = data["daily"]["temperature_2m_max"]
        min_temps = data["daily"]["temperature_2m_min"]
        forecast_df = pd.DataFrame(
            {
                "Date": dates,
                "Max Temp (°C)": max_temps,
                "Min Temp (°C)": min_temps,
            }
        )
        average_max_temp = sum(max_temps) / len(max_temps)

        return average_max_temp, forecast_df, None
    except requests.RequestException as error:
        return None, pd.DataFrame(), f"Weather forecast request failed: {error}"
    except KeyError:
        return None, pd.DataFrame(), "Weather forecast response was incomplete."


def get_weather_adjustment(temperature_celsius):
    """Return weather factor and insight based on temperature."""
    if temperature_celsius is None:
        return 1.0, "Weather unavailable → prediction shown without weather adjustment"

    if temperature_celsius > 30:
        return 1.2, "Hot weather → usage may increase"
    if temperature_celsius < 20:
        return 1.1, "Cold weather → usage may increase"
    return 1.0, "Normal conditions"


def build_chart_data(m1, m2, m3, predicted):
    """Create a dataframe for charts."""
    return pd.DataFrame(
        {
            "Period": ["Month 1", "Month 2", "Month 3", "Predicted"],
            "Units": [m1, m2, m3, predicted],
        }
    )


st.title("⚡ Electricity Consumption & Bill Prediction System")
st.subheader("Analyze recent usage, include Pune weather, and estimate your next bill")

st.info(
    "Enter the last three months of electricity units. The app predicts next month "
    "using weighted average, usage trend, Pune's 7-day weather forecast, and "
    "Pune/MSEDCL-style residential slab billing."
)

with st.sidebar:
    st.header("🌦️ Pune Forecast")
    st.caption("Weather data is fetched automatically from Open-Meteo. No API key is required.")

input_col, info_col = st.columns([1.1, 0.9])

with input_col:
    st.markdown("### 🔢 Last 3 Months Usage")

    m1 = st.number_input("Month 1 units", min_value=0.0, step=1.0, value=0.0)
    m2 = st.number_input("Month 2 units", min_value=0.0, step=1.0, value=0.0)
    m3 = st.number_input("Month 3 units", min_value=0.0, step=1.0, value=0.0)

    predict_clicked = st.button("🔮 Predict", use_container_width=True)

with info_col:
    st.markdown("### 🧠 Prediction Formula")
    st.write("**weighted** = m1×0.2 + m2×0.3 + m3×0.5")
    st.write("**growth** = ((m2 - m1) + (m3 - m2)) / 2")
    st.write("**trend** = m3 + growth")
    st.write("**basePrediction** = (weighted + trend) / 2")

if predict_clicked:
    if m1 <= 0 or m2 <= 0 or m3 <= 0:
        st.error("Please enter valid units greater than 0 for all three months.")
    else:
        forecast_temperature, forecast_df, weather_error = fetch_pune_forecast()
        prediction = predict_units(m1, m2, m3)
        weather_factor, insight = get_weather_adjustment(forecast_temperature)

        final_prediction = prediction["base_prediction"] * weather_factor
        bill_details = calculate_bill(final_prediction)
        predicted_bill = bill_details["total_bill"]

        st.markdown("## 📊 Prediction Dashboard")

        card1, card2, card3, card4 = st.columns(4)
        card1.metric(
            "🌡️ Pune Forecast Avg Max",
            "Unavailable" if forecast_temperature is None else f"{forecast_temperature:.1f}°C",
        )
        card2.metric("⚡ Predicted Units", f"{final_prediction:.2f}")
        card3.metric("💰 Predicted Bill", f"₹{predicted_bill:.2f}")
        card4.metric("🌦️ Weather Factor", f"{weather_factor:.1f}x")

        if weather_error:
            st.warning(weather_error)

        st.success(insight)
        st.caption(
            "Bill is an estimate using Pune residential slab rates, fixed charge, "
            "and 5% electricity duty. Official bills may include FAC, meter rent, "
            "subsidies, arrears, and other adjustments."
        )

        if not forecast_df.empty:
            with st.expander("🌦️ 7-Day Pune Weather Forecast", expanded=False):
                st.dataframe(forecast_df, use_container_width=True, hide_index=True)

        with st.expander("💰 MSEDCL-Style Bill Breakdown", expanded=True):
            slab_df = pd.DataFrame(bill_details["breakdown"])
            if not slab_df.empty:
                slab_df["Rate"] = slab_df["Rate"].map(lambda value: f"₹{value:.2f}/unit")
                slab_df["Amount"] = slab_df["Amount"].map(lambda value: f"₹{value:.2f}")
                st.dataframe(slab_df, use_container_width=True, hide_index=True)

            bill_col1, bill_col2, bill_col3 = st.columns(3)
            bill_col1.metric("Energy Charges", f"₹{bill_details['energy_charge']:.2f}")
            bill_col2.metric("Fixed Charges", f"₹{bill_details['fixed_charge']:.2f}")
            bill_col3.metric("Electricity Duty", f"₹{bill_details['electricity_duty']:.2f}")

        with st.expander("🧮 Calculation Breakdown", expanded=True):
            breakdown = pd.DataFrame(
                {
                    "Metric": ["Weighted", "Growth", "Trend", "Base Prediction", "Final Prediction"],
                    "Value": [
                        prediction["weighted"],
                        prediction["growth"],
                        prediction["trend"],
                        prediction["base_prediction"],
                        final_prediction,
                    ],
                }
            )
            st.dataframe(breakdown, use_container_width=True, hide_index=True)

        chart_data = build_chart_data(m1, m2, m3, final_prediction)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("### 📈 Consumption Trend")
            line_chart = px.line(
                chart_data,
                x="Period",
                y="Units",
                markers=True,
                title="Month-wise Consumption Trend",
            )
            line_chart.update_traces(line=dict(width=4), marker=dict(size=10))
            st.plotly_chart(line_chart, use_container_width=True)

        with chart_col2:
            st.markdown("### 📊 Units Comparison")
            bar_chart = px.bar(
                chart_data,
                x="Period",
                y="Units",
                color="Period",
                title="Actual vs Predicted Units",
            )
            st.plotly_chart(bar_chart, use_container_width=True)

        st.markdown("### 💡 Energy Saving Suggestions")
        st.write("- Turn off unused appliances and standby devices.")
        st.write("- Reduce AC usage during hot afternoons.")
        st.write("- Track monthly consumption to avoid high bill slabs.")
else:
    st.markdown("## 📌 Output will appear here after prediction")
    st.caption("Fill all three month values and click Predict.")

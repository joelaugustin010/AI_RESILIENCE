import os
from datetime import datetime, timezone

import requests
import streamlit as st

API_URL = "https://api.airvisual.com/v2/city"

POLLUTANTS = {
    "p2": "PM2.5",
    "p1": "PM10",
    "o3": "Ozone (O3)",
    "n2": "Nitrogen dioxide (NO2)",
    "s2": "Sulfur dioxide (SO2)",
    "co": "Carbon monoxide (CO)",
}

AQI_CATEGORIES = [
    (50, "Good"),
    (100, "Moderate"),
    (150, "Unhealthy for sensitive groups"),
    (200, "Unhealthy"),
    (300, "Very unhealthy"),
    (500, "Hazardous"),
]


def classify_aqi(aqi):
    for upper, label in AQI_CATEGORIES:
        if aqi <= upper:
            return label
    return "Beyond the standard US AQI range"


def health_advice(aqi):
    if aqi <= 50:
        return [
            "Air quality is generally satisfactory.",
            "Usual outdoor activities are generally fine.",
        ]
    elif aqi <= 100:
        return [
            "Air quality is acceptable for most people.",
            "Unusually sensitive people should watch for symptoms.",
        ]
    elif aqi <= 150:
        return [
            "Children, older adults and people with heart or lung "
            "conditions should reduce prolonged or heavy outdoor exertion.",
            "Consider moving strenuous activities indoors if symptoms occur.",
        ]
    elif aqi <= 200:
        return [
            "Everyone should consider reducing prolonged or heavy "
            "outdoor exertion.",
            "Sensitive groups should avoid strenuous outdoor activities.",
        ]
    elif aqi <= 300:
        return [
            "Avoid strenuous outdoor activity and reduce exposure.",
            "Sensitive groups should remain indoors as much as possible.",
        ]
    else:
        return [
            "Avoid outdoor exertion and minimise exposure.",
            "Follow local health and pollution advisories.",
        ]


@st.cache_data(ttl=600)
def fetch_kochi_data(api_key):
    response = requests.get(
        API_URL,
        params={
            "city": "Kochi",
            "state": "Kerala",
            "country": "India",
            "key": api_key,
        },
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("status") != "success":
        raise ValueError(
            "IQAir returned an unsuccessful response. "
            "Check API access, limits and location support."
        )

    data = result.get("data", {})

    # Do not accidentally display another city's data.
    if (
        data.get("city", "").strip().casefold() != "kochi"
        or data.get("state", "").strip().casefold() != "kerala"
        or data.get("country", "").strip().casefold() != "india"
    ):
        raise ValueError("The API did not confirm the requested Kochi location.")

    return data


def show_air_quality():
    st.title("🌍 Kochi Live Air Quality")
    st.caption("AI_RESILIENCE | Data source: IQAir AirVisual API")

    api_key = (
        st.secrets.get("IQAIR_API_KEY", "")
        if hasattr(st, "secrets")
        else ""
    ) or os.getenv("IQAIR_API_KEY", "")

    if not api_key:
        st.error(
            "API key missing. Add IQAIR_API_KEY to your "
            "environment variables or Streamlit secrets."
        )
        return

    if st.button("🔄 Refresh Kochi data"):
        fetch_kochi_data.clear()

    try:
        with st.spinner("Fetching the latest available readings..."):
            data = fetch_kochi_data(api_key)
    except requests.RequestException:
        st.error("Unable to connect to IQAir. Please try again later.")
        return
    except (ValueError, KeyError) as exc:
        st.warning(str(exc))
        return

    current = data.get("current", {})
    pollution = current.get("pollution", {})
    weather = current.get("weather", {})
    units = data.get("units", {})

    st.subheader(
        f"{data.get('city', 'Kochi')}, "
        f"{data.get('state', 'Kerala')}, "
        f"{data.get('country', 'India')}"
    )

    aqi = pollution.get("aqius")

    if aqi is not None:
        st.metric("US Air Quality Index", aqi)
        st.write("Category:", classify_aqi(aqi))
        st.write(
            "Dominant pollutant:",
            POLLUTANTS.get(
                pollution.get("mainus"),
                pollution.get("mainus", "Not reported"),
            ),
        )

        st.subheader("Health recommendations")
        for advice in health_advice(aqi):
            st.write(f"• {advice}")
    else:
        st.warning("A current US AQI reading was not provided.")

    st.caption(
        "AQI measurement time (UTC): "
        + str(pollution.get("ts", "Not provided"))
    )

    cn_aqi = pollution.get("aqicn")
    if cn_aqi is not None:
        st.write("Chinese AQI (separate scale):", cn_aqi)

    st.subheader("Available pollutant concentrations")

    found_pollutant = False

    for code, name in POLLUTANTS.items():
        details = pollution.get(code)
        if not isinstance(details, dict):
            continue

        concentration = details.get("conc")
        if concentration is None:
            continue

        found_pollutant = True
        unit = units.get(code, "unit not specified")
        st.write(f"**{name}:** {concentration} {unit}")

    if not found_pollutant:
        st.info(
            "Individual pollutant concentrations were not returned. "
            "Availability depends on the IQAir API subscription."
        )

    st.subheader("Current weather")

    weather_fields = {
        "Temperature": ("tp", "°C"),
        "Humidity": ("hu", "%"),
        "Atmospheric pressure": ("pr", "hPa"),
        "Wind speed": ("ws", "m/s"),
        "Wind direction": ("wd", "degrees"),
        "Heat index": ("heatIndex", "°C"),
    }

    cols = st.columns(3)
    for i, (label, (key, unit)) in enumerate(weather_fields.items()):
        value = weather.get(key)
        with cols[i % 3]:
            if value is not None:
                st.metric(label, f"{value} {unit}")

    st.caption(
        "Weather observation time (UTC): "
        + str(weather.get("ts", "Not provided"))
    )

    location = data.get("location", {})
    coordinates = location.get("coordinates")

    if coordinates:
        st.write(
            "Reported coordinates (longitude, latitude):",
            coordinates,
        )

    st.info(
        "Readings reflect the latest data available from IQAir and may "
        "not represent every neighbourhood in Kochi. AQI-based advice is "
        "general guidance, not a medical diagnosis."
    )

    st.caption(
        "Last retrieved (UTC): "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )


show_air_quality()

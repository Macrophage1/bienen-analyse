import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from streamlit_autorefresh import st_autorefresh

# ----- DATEIEN UND PFAD -----
ROHDATEI = "/Users/johanneszabka/Library/CloudStorage/OneDrive-Persönlich/Dokumente/Sensor/waagen_log.csv"
BEREINIGTE_CSV = "bereinigt.csv"

# ----- FUNKTION: PARSEN DER ROHDATEN -----
def parse_rohdaten(pfad):
    daten = []
    with open(pfad, 'r', encoding='utf-8') as file:
        for zeile in file:
            zeile = zeile.strip()
            if not zeile:
                continue
            teile = zeile.split(",")
            if len(teile) < 3:
                continue
            datum_uhrzeit = teile[0]
            w1 = teile[1]
            w2 = teile[2]
            try:
                dt = datetime.strptime(datum_uhrzeit, "%Y-%m-%d %H:%M")
                t1 = re.search(r"T:\s*([\d\.,]+)", w1)
                h1 = re.search(r"H:\s*([\d\.,]+)", w1)
                g1 = re.search(r"Gewicht:\s*(-?[\d\.,]+)", w1)
                t2 = re.search(r"T:\s*([\d\.,]+)", w2)
                h2 = re.search(r"H:\s*([\d\.,]+)", w2)
                g2 = re.search(r"Gewicht:\s*(-?[\d\.,]+)", w2)

                daten.append({
                    "Datum": dt.date(),
                    "Uhrzeit": dt.time(),
                    "T1": float(t1.group(1).replace(",", ".")) if t1 else None,
                    "H1": float(h1.group(1).replace(",", ".")) if h1 else None,
                    "G1": float(g1.group(1).replace(",", ".")) if g1 else None,
                    "T2": float(t2.group(1).replace(",", ".")) if t2 else None,
                    "H2": float(h2.group(1).replace(",", ".")) if h2 else None,
                    "G2": float(g2.group(1).replace(",", ".")) if g2 else None,
                })
            except Exception as e:
                print(f"Fehler beim Parsen: {zeile} => {e}")
    return pd.DataFrame(daten)

# ----- STREAMLIT SETUP -----
st.set_page_config(page_title="Bienenbeuten Analyse", layout="wide")
# Auto-Refresh alle 3600000 ms = 1 Stunde
st_autorefresh(interval=3600000, limit=None, key="auto-hourly-refresh")

st.title("🐝 Bienenbeuten-Datenanalyse")

df = parse_rohdaten(ROHDATEI)
if df.empty:
    st.error("Keine gültigen Daten gefunden.")
    st.stop()

# Bereinigte Datei speichern
df.to_csv(BEREINIGTE_CSV, index=False)

# ----- DATUM UND FILTER -----
st.sidebar.header("🔍 Filteroptionen")

# SessionState für Startdatum
if "startdatum" not in st.session_state:
    st.session_state.startdatum = df["Datum"].min()

col1, col2, col3 = st.sidebar.columns([1, 2, 1])
with col1:
    if st.button("←"):
        st.session_state.startdatum -= timedelta(days=1)
with col3:
    if st.button("→"):
        st.session_state.startdatum += timedelta(days=1)
with col2:
    st.date_input("Startdatum", key="startdatum")

zeitraum = st.sidebar.selectbox("Zeitraum", ["Gesamt", "1 Tag", "7 Tage", "1 Monat"])
völker = st.sidebar.multiselect("Volk auswählen", ["Volk 1", "Volk 2"], default=["Volk 1", "Volk 2"])
werte = st.sidebar.multiselect("Werte auswählen", ["Temperatur", "Luftfeuchtigkeit", "Gewicht"], default=["Temperatur", "Luftfeuchtigkeit", "Gewicht"])

# ----- ZEITRAUM FILTERN -----
df["Datetime"] = pd.to_datetime(df["Datum"].astype(str) + " " + df["Uhrzeit"].astype(str))
startdatum = st.session_state.startdatum
if zeitraum == "1 Tag":
    enddatum = startdatum + timedelta(days=1)
elif zeitraum == "7 Tage":
    enddatum = startdatum + timedelta(days=7)
elif zeitraum == "1 Monat":
    enddatum = startdatum + timedelta(days=30)
else:
    enddatum = df["Datum"].max() + timedelta(days=1)

df = df[(df["Datetime"] >= pd.to_datetime(startdatum)) & (df["Datetime"] < pd.to_datetime(enddatum))]

# ----- DIAGRAMM -----
st.subheader("📈 Zeitverlauf")

fig, ax1 = plt.subplots(figsize=(14, 5))
ax2 = ax1.twinx()

farben = {
    "T1": "tab:blue", "H1": "tab:cyan", "G1": "tab:gray",
    "T2": "tab:red", "H2": "tab:orange", "G2": "tab:green"
}

if "Volk 1" in völker:
    if "Temperatur" in werte:
        ax1.plot(df["Datetime"], df["T1"], label="Temperatur V1", color=farben["T1"])
    if "Luftfeuchtigkeit" in werte:
        ax1.plot(df["Datetime"], df["H1"], label="Luftfeuchte V1", color=farben["H1"])
    if "Gewicht" in werte:
        ax2.plot(df["Datetime"], df["G1"], label="Gewicht V1", linestyle="--", color=farben["G1"])

if "Volk 2" in völker:
    if "Temperatur" in werte:
        ax1.plot(df["Datetime"], df["T2"], label="Temperatur V2", color=farben["T2"])
    if "Luftfeuchtigkeit" in werte:
        ax1.plot(df["Datetime"], df["H2"], label="Luftfeuchte V2", color=farben["H2"])
    if "Gewicht" in werte:
        ax2.plot(df["Datetime"], df["G2"], label="Gewicht V2", linestyle="--", color=farben["G2"])

# Achsen & Formatierung
ax1.set_xlabel("Zeit")
ax1.set_ylabel("Temperatur / Luftfeuchtigkeit")
ax2.set_ylabel("Gewicht (g)")
ax1.xaxis.set_major_locator(mdates.HourLocator(interval=6))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m %H:%M'))
fig.autofmt_xdate()
fig.legend(loc="upper right")
ax1.grid(True)

st.pyplot(fig)

# ----- DOWNLOAD -----
st.sidebar.markdown("⬇️ [Bereinigte CSV herunterladen](bereinigt.csv)")

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

# Datei für die Datenspeicherung (simpel als JSON)
DATA_FILE = "spielerplus_data.json"

# Daten laden oder initialisieren
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": [], "sessions": [], "points": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

st.set_page_config(page_title="Team Manager & Scoreboard", layout="wide")
st.title("🏆 Team Manager & Punkteliga")

# Seitennavigation
tab1, tab2, tab3 = st.tabs(["📅 Kalender & Training", "📊 Scoreboard / Rangliste", "👤 Spieler-Registrierung"])

# ----------------------------------------------------
# TAB 3: SPIELER-REGISTRIERUNG
# ----------------------------------------------------
with tab3:
    st.header("Als neuer Spieler registrieren")
    with st.form("reg_form", clear_on_submit=True):
        name = st.text_input("Vollständiger Name")
        birthdate = st.date_input("Geburtsdatum", min_value=datetime(1950, 1, 1))
        # Profilbild-Upload (wird im echten Betrieb als Base64 oder Pfad gespeichert, hier als Platzhalter)
        photo = st.file_uploader("Profilbild hochladen", type=["png", "jpg", "jpeg"])
        
        submitted = st.form_submit_button("Registrieren")
        if submitted:
            if name:
                if name not in [p["name"] for p in data["players"]]:
                    data["players"].append({
                        "name": name,
                        "birthdate": str(birthdate),
                        "active": True
                    })
                    save_data(data)
                    st.success(f"Spieler '{name}' erfolgreich registriert!")
                    st.rerun()
                else:
                    st.error("Dieser Name existiert bereits.")
            else:
                st.error("Bitte gib einen Namen ein.")

# ----------------------------------------------------
# ADMINBEREICH (Für Trainer-Funktionen im Kalender)
# ----------------------------------------------------
st.sidebar.header("🔑 Trainer-Bereich")
admin_password = st.sidebar.text_input("Admin-Passwort", type="password")
is_admin = (admin_password == "admin") # Standard-Passwort: admin

if is_admin:
    st.sidebar.success("Trainer-Modus aktiv!")
    st.sidebar.subheader("Neues Training anlegen")
    t_date = st.sidebar.date_input("Datum für Training")
    t_time = st.sidebar.time_input("Uhrzeit")
    
    if st.sidebar.button("Trainingseinheit erstellen"):
        session_id = f"{t_date}_{t_time.strftime('%H-%M')}"
        if session_id not in [s["id"] for s in data["sessions"]]:
            data["sessions"].append({"id": session_id, "date": str(t_date), "time": str(t_time)})
            
            # Automatisch alle Spieler für diesen Tag als "Anwesend" anlegen
            for player in data["players"]:
                if player["active"]:
                    data["points"].append({
                        "session_id": session_id,
                        "date": str(t_date),
                        "player": player["name"],
                        "status": "Anwesend",
                        "points": 0
                    })
            save_data(data)
            st.sidebar.success("Training und Anwesenheitsliste erstellt!")
            st.rerun()
        else:
            st.sidebar.error("Dieses Training existiert bereits.")

# ----------------------------------------------------
# TAB 1: KALENDER & TRAINING
# ----------------------------------------------------
with tab1:
    st.header("Trainingsübersicht")
    
    if not data["sessions"]:
        st.info("Noch keine Trainingstermine eingetragen. (Trainer kann diese links in der Sidebar anlegen)")
    else:
        # Trainings auswählen
        session_options = {s["id"]: f"Training am {s['date']} um {s['time']}" for s in data["sessions"]}
        selected_session = st.selectbox("Wähle ein Training aus:", options=list(session_options.keys()), format_func=lambda x: session_options[x])
        
        st.subheader("Teilnehmerliste & Punktevergabe")
        
        # Einträge für die gewählte Session filtern
        session_entries = [e for e in data["points"] if e["session_id"] == selected_session]
        
        for entry in session_entries:
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.write(f"**{entry['player']}**")
                
            with col2:
                if is_admin:
                    # Trainer darf den Status ändern
                    current_idx = 0 if entry["status"] == "Anwesend" else 1
                    new_status = st.selectbox(f"Status für {entry['player']}", ["Anwesend", "Abwesend"], index=current_idx, key=f"status_{entry['player']}_{selected_session}")
                    if new_status != entry["status"]:
                        entry["status"] = new_status
                        if new_status == "Abwesend":
                            entry["points"] = 0 # Punkte nullen bei Abwesenheit
                        save_data(data)
                        st.rerun()
                else:
                    st.write(f"Status: *{entry['status']}*")
                    
            with col3:
                if entry["status"] == "Anwesend":
                    # Wenn anwesend, darf der Spieler seine Punkte eintragen
                    pts = st.number_input(f"Punkte für {entry['player']}", min_value=0, value=int(entry["points"]), key=f"pts_{entry['player']}_{selected_session}")
                    if pts != entry["points"]:
                        entry["points"] = pts
                        save_data(data)
                else:
                    st.write("❌ Abwesend (Punkte gesperrt)")
            st.divider()

# ----------------------------------------------------
# TAB 2: SCOREBOARD / RANGLISTE
# ----------------------------------------------------
with tab2:
    st.header("🏆 Rangliste")
    
    if not data["points"]:
        st.info("Noch keine Punkte vorhanden.")
    else:
        df = pd.DataFrame(data["points"])
        df["date"] = pd.to_datetime(df["date"])
        df["Monat"] = df["date"].dt.strftime("%Y-%m (%B)")
        
        # Monatsfilter oben einbauen
        all_months = ["Gesamt (Alle Monate)"] + sorted(df["Monat"].unique().tolist(), reverse=True)
        selected_month = st.selectbox("Filter nach Monat:", all_months)
        
        # Daten filtern basierend auf Auswahl
        if selected_month != "Gesamt (Alle Monate)":
            filtered_df = df[df["Monat"] == selected_month]
        else:
            filtered_df = df
            
        # Punkte zusammenrechnen (Gruppieren nach Spieler)
        leaderboard = filtered_df.groupby("player")["points"].sum().reset_index()
        leaderboard.columns = ["Spieler", "Gesamtpunkte"]
        
        # Nach Punkten sortieren und Platzierung hinzufügen
        leaderboard = leaderboard.sort_values(by="Gesamtpunkte", ascending=False).reset_index(drop=True)
        leaderboard.index = leaderboard.index + 1
        leaderboard.index.name = "Platz"
        
        st.dataframe(leaderboard, use_container_width=True)

import streamlit as st
import pandas as pd
import json
import os
import uuid
from datetime import date, time, datetime

# ==========================================================
# KONFIGURATION & KONSTANTEN
# ==========================================================
st.set_page_config(page_title="Team Manager", page_icon="⚽", layout="wide")

DATA_FILE = "team_data.json"
PHOTOS_DIR = "player_photos"
ADMIN_PASSWORD = "admin"

MONTH_NAMES_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

os.makedirs(PHOTOS_DIR, exist_ok=True)


# ==========================================================
# DATEN LADEN / SPEICHERN
# ==========================================================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"players": [], "trainings": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"players": [], "trainings": []}
            data = json.loads(content)
            if "players" not in data:
                data["players"] = []
            if "trainings" not in data:
                data["trainings"] = []
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {"players": [], "trainings": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_month(month_key):
    """month_key im Format 'YYYY-MM' -> 'Monatsname JJJJ'"""
    year, month = month_key.split("-")
    return f"{MONTH_NAMES_DE[int(month) - 1]} {year}"


# ==========================================================
# SESSION STATE INITIALISIEREN
# ==========================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# ==========================================================
# SIDEBAR: TRAINER-BEREICH (ADMIN LOGIN)
# ==========================================================
st.sidebar.title("⚙️ Trainer-Bereich")

if not st.session_state.is_admin:
    st.sidebar.info("Melde dich als Trainer an, um Trainingseinheiten anzulegen und die Anwesenheit zu verwalten.")
    admin_pw_input = st.sidebar.text_input("Admin-Passwort", type="password", key="admin_pw_input")
    if st.sidebar.button("🔐 Als Trainer anmelden"):
        if admin_pw_input == ADMIN_PASSWORD:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.sidebar.error("Falsches Passwort.")
else:
    st.sidebar.success("✅ Angemeldet als Trainer")
    if st.sidebar.button("🚪 Abmelden"):
        st.session_state.is_admin = False
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Sportteam-Verwaltung – kostenlos gehostet auf Streamlit Community Cloud")


# ==========================================================
# HAUPTBEREICH
# ==========================================================
st.title("⚽ Team Manager")

data = load_data()

tab1, tab2, tab3 = st.tabs([
    "📅 Kalender & Training",
    "🏆 Scoreboard / Rangliste",
    "📝 Spieler-Registrierung"
])


# ==========================================================
# TAB 1: KALENDER & TRAINING
# ==========================================================
with tab1:
    st.header("📅 Kalender & Training")

    active_players = [p for p in data["players"] if p.get("active", True)]

    # --- Admin: Neues Training anlegen ---
    if st.session_state.is_admin:
        with st.expander("➕ Neues Training anlegen", expanded=len(data["trainings"]) == 0):
            with st.form("new_training_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    training_date = st.date_input("Datum", value=date.today())
                with col_b:
                    training_time = st.time_input("Uhrzeit", value=time(18, 0))

                submitted = st.form_submit_button("Training erstellen")
                if submitted:
                    date_str = training_date.isoformat()
                    time_str = training_time.strftime("%H:%M")

                    already_exists = any(
                        t["date"] == date_str and t["time"] == time_str
                        for t in data["trainings"]
                    )

                    if already_exists:
                        st.warning("An diesem Datum/Uhrzeit existiert bereits ein Training.")
                    elif not active_players:
                        st.warning("Es sind keine aktiven Spieler registriert. Training wurde trotzdem angelegt, aber ohne Teilnehmer.")
                        new_training = {
                            "id": str(uuid.uuid4()),
                            "date": date_str,
                            "time": time_str,
                            "attendance": {}
                        }
                        data["trainings"].append(new_training)
                        save_data(data)
                        st.rerun()
                    else:
                        # Automatische Anwesenheit für alle aktiven Spieler
                        attendance = {
                            p["name"]: {"status": "Anwesend", "points": 0}
                            for p in active_players
                        }
                        new_training = {
                            "id": str(uuid.uuid4()),
                            "date": date_str,
                            "time": time_str,
                            "attendance": attendance
                        }
                        data["trainings"].append(new_training)
                        save_data(data)
                        st.success(
                            f"Training am {date_str} um {time_str} Uhr wurde erstellt. "
                            f"{len(active_players)} Spieler wurden automatisch als 'Anwesend' markiert."
                        )
                        st.rerun()

    st.markdown("---")

    if not data["trainings"]:
        st.info("Noch keine Trainingseinheiten angelegt. " +
                ("Nutze den Bereich oben, um eines zu erstellen." if st.session_state.is_admin
                 else "Bitte warte, bis der Trainer ein Training anlegt."))
    else:
        sorted_trainings = sorted(
            data["trainings"], key=lambda t: (t["date"], t["time"]), reverse=True
        )
        training_options = {
            f'{t["date"]} um {t["time"]} Uhr  ·  {len(t["attendance"])} Spieler': t["id"]
            for t in sorted_trainings
        }
        selected_label = st.selectbox("📆 Trainingstag auswählen", list(training_options.keys()))
        selected_id = training_options[selected_label]

        # Referenz auf das ausgewählte Training in data finden
        training = next(t for t in data["trainings"] if t["id"] == selected_id)

        st.subheader(f'Anwesenheit & Punkte – {training["date"]} um {training["time"]} Uhr')

        if not training["attendance"]:
            st.warning("Für diesen Trainingstag sind keine Spieler erfasst.")
        else:
            all_player_names = [p["name"] for p in data["players"]]
            login_options = ["– Kein Login (nur Ansicht) –"] + all_player_names
            logged_in_player = st.selectbox(
                "👤 Als welcher Spieler bist du angemeldet? (zum Eintragen deiner eigenen Punkte)",
                login_options,
                key=f"login_select_{selected_id}"
            )

            st.markdown("&nbsp;")
            header_cols = st.columns([3, 2, 2, 2])
            header_cols[0].markdown("**Spieler**")
            header_cols[1].markdown("**Status**")
            header_cols[2].markdown("**Punkte**")
            header_cols[3].markdown("**Aktion**")
            st.markdown("---")

            for player_name in list(training["attendance"].keys()):
                info = training["attendance"][player_name]
                player_obj = next((p for p in data["players"] if p["name"] == player_name), None)

                row_cols = st.columns([3, 2, 2, 2])

                # --- Spalte: Name & Foto ---
                with row_cols[0]:
                    inner_cols = st.columns([1, 3])
                    with inner_cols[0]:
                        if player_obj and player_obj.get("photo") and os.path.exists(player_obj["photo"]):
                            st.image(player_obj["photo"], width=40)
                        else:
                            st.markdown("👤")
                    with inner_cols[1]:
                        st.markdown(f"**{player_name}**")

                # --- Spalte: Status ---
                with row_cols[1]:
                    if st.session_state.is_admin:
                        current_index = 0 if info["status"] == "Anwesend" else 1
                        new_status = st.selectbox(
                            "Status", ["Anwesend", "Abwesend"],
                            index=current_index,
                            key=f"status_{selected_id}_{player_name}",
                            label_visibility="collapsed"
                        )
                        if new_status != info["status"]:
                            info["status"] = new_status
                            if new_status == "Abwesend":
                                info["points"] = 0
                            save_data(data)
                            st.rerun()
                    else:
                        if info["status"] == "Anwesend":
                            st.markdown("🟢 Anwesend")
                        else:
                            st.markdown("🔴 Abwesend")

                # --- Spalte: Punkte ---
                with row_cols[2]:
                    is_owner = (logged_in_player == player_name)
                    can_edit_points = (info["status"] == "Anwesend") and (st.session_state.is_admin or is_owner)

                    if info["status"] == "Abwesend":
                        st.markdown("**0** (gesperrt)")
                        entered_points = 0
                    else:
                        entered_points = st.number_input(
                            "Punkte",
                            min_value=0,
                            max_value=1000,
                            value=int(info["points"]),
                            step=1,
                            key=f"points_{selected_id}_{player_name}",
                            disabled=not can_edit_points,
                            label_visibility="collapsed"
                        )

                # --- Spalte: Speichern-Button ---
                with row_cols[3]:
                    if info["status"] == "Anwesend" and can_edit_points:
                        if st.button("💾 Speichern", key=f"save_{selected_id}_{player_name}"):
                            info["points"] = entered_points
                            save_data(data)
                            st.success(f"Punkte für {player_name} gespeichert.")
                            st.rerun()
                    elif info["status"] == "Abwesend":
                        st.caption("Eingabe gesperrt")
                    else:
                        st.caption("–")

                st.markdown("&nbsp;")


# ==========================================================
# TAB 2: SCOREBOARD / RANGLISTE
# ==========================================================
with tab2:
    st.header("🏆 Scoreboard / Rangliste")

    if not data["trainings"]:
        st.info("Es liegen noch keine Trainingsdaten vor. Sobald Trainings mit Punkten erfasst wurden, erscheint hier die Rangliste.")
    else:
        # Verfügbare Monate ermitteln
        month_keys = sorted({t["date"][:7] for t in data["trainings"]}, reverse=True)
        filter_options = ["Gesamtzeit"] + [format_month(m) for m in month_keys]

        selected_filter = st.selectbox("🗓️ Zeitraum auswählen", filter_options)

        if selected_filter == "Gesamtzeit":
            filtered_trainings = data["trainings"]
        else:
            target_month = month_keys[filter_options.index(selected_filter) - 1]
            filtered_trainings = [t for t in data["trainings"] if t["date"][:7] == target_month]

        # Punkte pro Spieler summieren
        totals = {p["name"]: 0 for p in data["players"]}
        trainings_count = {p["name"]: 0 for p in data["players"]}

        for t in filtered_trainings:
            for pname, info in t["attendance"].items():
                if pname not in totals:
                    totals[pname] = 0
                    trainings_count[pname] = 0
                totals[pname] += info.get("points", 0)
                if info.get("status") == "Anwesend":
                    trainings_count[pname] += 1

        if not totals:
            st.info("Noch keine Spieler registriert.")
        else:
            rows = [
                {"Spieler": name, "Punkte": pts, "Trainings (anwesend)": trainings_count.get(name, 0)}
                for name, pts in totals.items()
            ]
            df = pd.DataFrame(rows)
            df = df.sort_values(by="Punkte", ascending=False).reset_index(drop=True)
            df.insert(0, "Platz", df.index + 1)

            # --- Podium für Top 3 ---
            if len(df) > 0:
                podium_cols = st.columns(min(3, len(df)))
                medals = ["🥇", "🥈", "🥉"]
                for i in range(min(3, len(df))):
                    with podium_cols[i]:
                        st.metric(
                            label=f'{medals[i]} {df.iloc[i]["Spieler"]}',
                            value=f'{df.iloc[i]["Punkte"]} Punkte'
                        )

            st.markdown("---")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Platz": st.column_config.NumberColumn("Platz", width="small"),
                    "Spieler": st.column_config.TextColumn("Spieler"),
                    "Punkte": st.column_config.NumberColumn("Punkte", width="small"),
                    "Trainings (anwesend)": st.column_config.NumberColumn("Trainings (anwesend)", width="medium"),
                }
            )


# ==========================================================
# TAB 3: SPIELER-REGISTRIERUNG
# ==========================================================
with tab3:
    st.header("📝 Spieler-Registrierung")
    st.write("Neue Mitglieder können sich hier für das Team registrieren.")

    with st.form("register_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Name des Spielers")
        with col2:
            new_birthdate = st.date_input(
                "Geburtsdatum",
                value=date(2000, 1, 1),
                min_value=date(1930, 1, 1),
                max_value=date.today()
            )

        new_photo = st.file_uploader("Profilbild hochladen (optional)", type=["png", "jpg", "jpeg"])

        submitted = st.form_submit_button("✅ Registrieren")

        if submitted:
            clean_name = new_name.strip()
            if not clean_name:
                st.error("Bitte gib einen Namen ein.")
            elif any(p["name"].lower() == clean_name.lower() for p in data["players"]):
                st.error(f"Ein Spieler namens '{clean_name}' ist bereits registriert.")
            else:
                photo_path = None
                if new_photo is not None:
                    file_ext = os.path.splitext(new_photo.name)[1]
                    safe_name = "".join(c for c in clean_name if c.isalnum()) or "spieler"
                    unique_filename = f"{safe_name}_{uuid.uuid4().hex[:8]}{file_ext}"
                    photo_path = os.path.join(PHOTOS_DIR, unique_filename)
                    with open(photo_path, "wb") as f:
                        f.write(new_photo.getbuffer())

                new_player = {
                    "name": clean_name,
                    "birthdate": new_birthdate.isoformat(),
                    "photo": photo_path,
                    "active": True,
                    "registered_at": datetime.now().isoformat()
                }
                data["players"].append(new_player)
                save_data(data)
                st.success(f"🎉 {clean_name} wurde erfolgreich registriert!")
                st.rerun()

    st.markdown("---")
    st.subheader("Registrierte Spieler")

    if not data["players"]:
        st.info("Noch keine Spieler registriert.")
    else:
        header_cols = st.columns([1, 3, 3, 2])
        header_cols[1].markdown("**Name**")
        header_cols[2].markdown("**Geburtsdatum**")
        header_cols[3].markdown("**Status**")
        st.markdown("---")

        for player in sorted(data["players"], key=lambda p: p["name"]):
            row_cols = st.columns([1, 3, 3, 2])
            with row_cols[0]:
                if player.get("photo") and os.path.exists(player["photo"]):
                    st.image(player["photo"], width=45)
                else:
                    st.markdown("👤")
            with row_cols[1]:
                st.write(player["name"])
            with row_cols[2]:
                st.write(player["birthdate"])
            with row_cols[3]:
                if st.session_state.is_admin:
                    is_active = st.checkbox(
                        "Aktiv",
                        value=player.get("active", True),
                        key=f"active_toggle_{player['name']}"
                    )
                    if is_active != player.get("active", True):
                        player["active"] = is_active
                        save_data(data)
                        st.rerun()
                else:
                    st.write("🟢 Aktiv" if player.get("active", True) else "⚪ Inaktiv")

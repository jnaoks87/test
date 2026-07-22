import streamlit as st
import pandas as pd
import json
import os
import uuid
import calendar as cal_module
from datetime import date, time, datetime, timedelta

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

WEEKDAY_NAMES_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WEEKDAY_SHORT_DE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

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
# HILFSFUNKTIONEN: SPIELER
# ==========================================================
def get_player_by_id(players, pid):
    return next((p for p in players if p["id"] == pid), None)


def non_trainer_players(players):
    """Alle registrierten Spieler, die NICHT als Trainer markiert sind."""
    return [p for p in players if not p.get("is_trainer", False)]


def active_non_trainer_players(players):
    return [p for p in non_trainer_players(players) if p.get("active", True)]


def eligible_players_for_date(players, training_date_str):
    """Aktive Nicht-Trainer-Spieler, die am angegebenen Datum bereits registriert waren."""
    eligible = []
    for p in active_non_trainer_players(players):
        reg_date = p.get("registered_at", "1900-01-01T00:00:00")[:10]
        if reg_date <= training_date_str:
            eligible.append(p)
    return eligible


# ==========================================================
# HILFSFUNKTIONEN: TRAINING ANLEGEN
# ==========================================================
def create_training(data, date_str, start_time_str, end_time_str, series_id=None):
    """Legt ein einzelnes Training an, falls an diesem Datum/Uhrzeit noch keines existiert."""
    exists = any(t["date"] == date_str and t["time"] == start_time_str for t in data["trainings"])
    if exists:
        return False

    eligible = eligible_players_for_date(data["players"], date_str)
    attendance = {p["id"]: {"status": "Anwesend", "points": 0} for p in eligible}

    new_training = {
        "id": str(uuid.uuid4()),
        "date": date_str,
        "time": start_time_str,
        "end_time": end_time_str,
        "series_id": series_id,
        "attendance": attendance
    }
    data["trainings"].append(new_training)
    return True


# ==========================================================
# SESSION STATE INITIALISIEREN
# ==========================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "cal_year" not in st.session_state:
    st.session_state.cal_year = date.today().year
if "cal_month" not in st.session_state:
    st.session_state.cal_month = date.today().month
if "selected_training_id" not in st.session_state:
    st.session_state.selected_training_id = None


# ==========================================================
# SIDEBAR: TRAINER-BEREICH (ADMIN LOGIN)
# ==========================================================
st.sidebar.title("⚙️ Trainer-Bereich")

if not st.session_state.is_admin:
    st.sidebar.info("Melde dich als Trainer an, um Trainingseinheiten anzulegen und Anwesenheit/Punkte zu verwalten.")
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

    # ------------------------------------------------------
    # ADMIN: NEUES TRAINING (EINZELN ODER ALS SERIE) ANLEGEN
    # ------------------------------------------------------
    if st.session_state.is_admin:
        with st.expander("➕ Neues Training anlegen", expanded=len(data["trainings"]) == 0):
            training_mode = st.radio(
                "Art des Termins",
                ["Einzeltermin", "Wöchentliche Serie"],
                horizontal=True,
                key="training_mode_radio"
            )

            if training_mode == "Einzeltermin":
                with st.form("new_single_training_form", clear_on_submit=True):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        training_date = st.date_input("Datum", value=date.today())
                    with col_b:
                        start_t = st.time_input("Von", value=time(18, 0))
                    with col_c:
                        end_t = st.time_input("Bis", value=time(19, 30))

                    submitted = st.form_submit_button("Training erstellen")
                    if submitted:
                        if end_t <= start_t:
                            st.error("Die 'Bis'-Uhrzeit muss nach der 'Von'-Uhrzeit liegen.")
                        else:
                            date_str = training_date.isoformat()
                            created = create_training(
                                data, date_str,
                                start_t.strftime("%H:%M"),
                                end_t.strftime("%H:%M")
                            )
                            if created:
                                save_data(data)
                                st.success(f"Training am {date_str} wurde erstellt und Spieler automatisch eingetragen.")
                                st.rerun()
                            else:
                                st.warning("An diesem Datum/Uhrzeit existiert bereits ein Training.")

            else:  # Wöchentliche Serie
                with st.form("new_series_training_form", clear_on_submit=True):
                    weekday_choice = st.selectbox("Wochentag", WEEKDAY_NAMES_DE)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        series_start = st.date_input("Serie – Startdatum", value=date.today())
                    with col_b:
                        series_end = st.date_input("Serie – Enddatum", value=date.today() + timedelta(days=90))

                    col_c, col_d = st.columns(2)
                    with col_c:
                        series_start_time = st.time_input("Von", value=time(18, 0), key="series_from")
                    with col_d:
                        series_end_time = st.time_input("Bis", value=time(19, 30), key="series_to")

                    submitted_series = st.form_submit_button("Serie erstellen")
                    if submitted_series:
                        if series_end < series_start:
                            st.error("Das Enddatum der Serie muss nach dem Startdatum liegen.")
                        elif series_end_time <= series_start_time:
                            st.error("Die 'Bis'-Uhrzeit muss nach der 'Von'-Uhrzeit liegen.")
                        else:
                            target_weekday_index = WEEKDAY_NAMES_DE.index(weekday_choice)
                            series_uuid = str(uuid.uuid4())
                            current_day = series_start
                            created_count = 0
                            skipped_count = 0
                            while current_day <= series_end:
                                if current_day.weekday() == target_weekday_index:
                                    was_created = create_training(
                                        data, current_day.isoformat(),
                                        series_start_time.strftime("%H:%M"),
                                        series_end_time.strftime("%H:%M"),
                                        series_id=series_uuid
                                    )
                                    if was_created:
                                        created_count += 1
                                    else:
                                        skipped_count += 1
                                current_day += timedelta(days=1)
                            save_data(data)
                            st.success(
                                f"Serie erstellt: {created_count} Trainingstermine (jeden {weekday_choice}) "
                                f"wurden angelegt."
                                + (f" {skipped_count} bereits vorhandene Termine wurden übersprungen." if skipped_count else "")
                            )
                            st.rerun()

    st.markdown("---")

    # ------------------------------------------------------
    # KALENDERANSICHT
    # ------------------------------------------------------
    nav_cols = st.columns([1, 4, 1])
    with nav_cols[0]:
        if st.button("◀", key="prev_month"):
            m = st.session_state.cal_month - 1
            y = st.session_state.cal_year
            if m < 1:
                m = 12
                y -= 1
            st.session_state.cal_month = m
            st.session_state.cal_year = y
            st.rerun()
    with nav_cols[1]:
        st.markdown(
            f"<h3 style='text-align:center;'>{MONTH_NAMES_DE[st.session_state.cal_month - 1]} {st.session_state.cal_year}</h3>",
            unsafe_allow_html=True
        )
    with nav_cols[2]:
        if st.button("▶", key="next_month"):
            m = st.session_state.cal_month + 1
            y = st.session_state.cal_year
            if m > 12:
                m = 1
                y += 1
            st.session_state.cal_month = m
            st.session_state.cal_year = y
            st.rerun()

    if st.button("📍 Heute", key="today_btn"):
        st.session_state.cal_year = date.today().year
        st.session_state.cal_month = date.today().month
        st.rerun()

    trainings_by_date = {}
    for t in data["trainings"]:
        trainings_by_date.setdefault(t["date"], []).append(t)

    header_cols = st.columns(7)
    for i, h in enumerate(WEEKDAY_SHORT_DE):
        header_cols[i].markdown(f"<div style='text-align:center;'><b>{h}</b></div>", unsafe_allow_html=True)

    cal_obj = cal_module.Calendar(firstweekday=0)
    month_weeks = cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)

    for week in month_weeks:
        week_cols = st.columns(7)
        for i, day_num in enumerate(week):
            with week_cols[i]:
                if day_num == 0:
                    st.markdown("&nbsp;")
                else:
                    day_date = date(st.session_state.cal_year, st.session_state.cal_month, day_num)
                    day_str = day_date.isoformat()
                    is_today = day_date == date.today()
                    day_label = f"**:blue[{day_num}]**" if is_today else f"{day_num}"
                    st.markdown(day_label)

                    day_trainings = sorted(trainings_by_date.get(day_str, []), key=lambda x: x["time"])
                    for t in day_trainings:
                        is_selected = (t["id"] == st.session_state.selected_training_id)
                        btn_label = f'{"✅" if is_selected else "⚽"} {t["time"]}'
                        if st.button(btn_label, key=f'cal_btn_{t["id"]}'):
                            st.session_state.selected_training_id = t["id"]
                            st.rerun()

    st.markdown("---")

    # ------------------------------------------------------
    # AUSGEWÄHLTES TRAINING: ANWESENHEIT & PUNKTE
    # ------------------------------------------------------
    training = None
    if st.session_state.selected_training_id:
        training = next((t for t in data["trainings"] if t["id"] == st.session_state.selected_training_id), None)

    if training is None:
        st.info("Wähle im Kalender oben ein Training aus (⚽-Button), um Anwesenheit und Punkte zu sehen bzw. zu bearbeiten.")
    else:
        st.subheader(f'Anwesenheit & Punkte – {training["date"]}, {training["time"]}–{training.get("end_time", "?")} Uhr')

        if not training["attendance"]:
            st.warning("Für diesen Trainingstag sind keine Spieler erfasst.")
        else:
            # Namen für Login-Auswahl (nur Spieler, die an diesem Training teilnehmen)
            attendee_names = []
            for pid in training["attendance"].keys():
                p_obj = get_player_by_id(data["players"], pid)
                if p_obj:
                    attendee_names.append(p_obj["name"])
            attendee_names = sorted(attendee_names)

            login_options = ["– Kein Login (nur Ansicht) –"] + attendee_names
            logged_in_name = st.selectbox(
                "👤 Als welcher Spieler bist du angemeldet? (zum Eintragen deiner eigenen Punkte)",
                login_options,
                key=f"login_select_{training['id']}"
            )

            st.markdown("&nbsp;")
            header_row = st.columns([3, 2, 2, 2])
            header_row[0].markdown("**Spieler**")
            header_row[1].markdown("**Status**")
            header_row[2].markdown("**Punkte**")
            header_row[3].markdown("**Aktion**")
            st.markdown("---")

            for pid in list(training["attendance"].keys()):
                info = training["attendance"][pid]
                player_obj = get_player_by_id(data["players"], pid)
                if player_obj is None:
                    continue
                player_name = player_obj["name"]

                row_cols = st.columns([3, 2, 2, 2])

                with row_cols[0]:
                    inner_cols = st.columns([1, 3])
                    with inner_cols[0]:
                        if player_obj.get("photo") and os.path.exists(player_obj["photo"]):
                            st.image(player_obj["photo"], width=40)
                        else:
                            st.markdown("👤")
                    with inner_cols[1]:
                        st.markdown(f"**{player_name}**")

                with row_cols[1]:
                    if st.session_state.is_admin:
                        current_index = 0 if info["status"] == "Anwesend" else 1
                        new_status = st.selectbox(
                            "Status", ["Anwesend", "Abwesend"],
                            index=current_index,
                            key=f"status_{training['id']}_{pid}",
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

                with row_cols[2]:
                    is_owner = (logged_in_name == player_name)
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
                            key=f"points_{training['id']}_{pid}",
                            disabled=not can_edit_points,
                            label_visibility="collapsed"
                        )

                with row_cols[3]:
                    if info["status"] == "Anwesend" and can_edit_points:
                        if st.button("💾 Speichern", key=f"save_{training['id']}_{pid}"):
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

    ranked_players = non_trainer_players(data["players"])

    if not data["trainings"] or not ranked_players:
        st.info("Es liegen noch keine Trainingsdaten bzw. Spieler vor. Sobald Punkte erfasst wurden, erscheint hier die Rangliste.")
    else:
        # -------------------------------------------------
        # Monatsfilter
        # -------------------------------------------------
        month_keys_all = sorted({t["date"][:7] for t in data["trainings"]}, reverse=True)
        filter_options = ["Gesamtzeit"] + [format_month(m) for m in month_keys_all]
        selected_filter = st.selectbox("🗓️ Zeitraum auswählen", filter_options)

        if selected_filter == "Gesamtzeit":
            filtered_trainings = data["trainings"]
        else:
            target_month = month_keys_all[filter_options.index(selected_filter) - 1]
            filtered_trainings = [t for t in data["trainings"] if t["date"][:7] == target_month]

        # -------------------------------------------------
        # Punkte (gefiltert) + Trainingsanzahl pro Spieler
        # -------------------------------------------------
        totals = {p["id"]: 0 for p in ranked_players}
        trainings_count = {p["id"]: 0 for p in ranked_players}

        for t in filtered_trainings:
            for pid, info in t["attendance"].items():
                if pid not in totals:
                    continue  # Trainer oder gelöschte Spieler ignorieren
                totals[pid] += info.get("points", 0)
                if info.get("status") == "Anwesend":
                    trainings_count[pid] += 1

        # -------------------------------------------------
        # Monatssiege (immer über die GESAMTE Historie berechnet)
        # -------------------------------------------------
        monthly_wins = {p["id"]: 0 for p in ranked_players}
        trainings_by_month = {}
        for t in data["trainings"]:
            trainings_by_month.setdefault(t["date"][:7], []).append(t)

        for month_key, month_trainings in trainings_by_month.items():
            month_totals = {}
            for t in month_trainings:
                for pid, info in t["attendance"].items():
                    if pid not in monthly_wins:
                        continue
                    month_totals[pid] = month_totals.get(pid, 0) + info.get("points", 0)
            if month_totals:
                max_points = max(month_totals.values())
                if max_points > 0:
                    winners = [pid for pid, pts in month_totals.items() if pts == max_points]
                    for w in winners:
                        monthly_wins[w] += 1

        # -------------------------------------------------
        # Tabelle bauen
        # -------------------------------------------------
        rows = []
        for p in ranked_players:
            rows.append({
                "Spieler": p["name"],
                "Monatssiege": monthly_wins.get(p["id"], 0),
                "Punkte": totals.get(p["id"], 0),
                "Trainings (anwesend)": trainings_count.get(p["id"], 0),
            })

        df = pd.DataFrame(rows)
        df = df.sort_values(by=["Monatssiege", "Punkte"], ascending=[False, False]).reset_index(drop=True)
        df.insert(0, "Platz", df.index + 1)

        # Podium für Top 3
        if len(df) > 0:
            podium_cols = st.columns(min(3, len(df)))
            medals = ["🥇", "🥈", "🥉"]
            for i in range(min(3, len(df))):
                with podium_cols[i]:
                    st.metric(
                        label=f'{medals[i]} {df.iloc[i]["Spieler"]}',
                        value=f'{df.iloc[i]["Punkte"]} Punkte',
                        delta=f'{df.iloc[i]["Monatssiege"]} Monatssiege' if df.iloc[i]["Monatssiege"] > 0 else None
                    )

        st.markdown("---")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Platz": st.column_config.NumberColumn("Platz", width="small"),
                "Spieler": st.column_config.TextColumn("Spieler"),
                "Monatssiege": st.column_config.NumberColumn("🏅 Monatssiege", width="small"),
                "Punkte": st.column_config.NumberColumn("Punkte", width="small"),
                "Trainings (anwesend)": st.column_config.NumberColumn("Trainings (anwesend)", width="medium"),
            }
        )
        st.caption("Die Rangliste wird zuerst nach Monatssiegen und danach nach der Gesamtpunktzahl im gewählten Zeitraum sortiert.")


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
        is_trainer_checkbox = st.checkbox(
            "Ich melde mich als Trainer/Betreuer an (wird nicht in Trainings & Rangliste geführt)"
        )

        submitted = st.form_submit_button("✅ Registrieren")

        if submitted:
            clean_name = new_name.strip()
            if not clean_name:
                st.error("Bitte gib einen Namen ein.")
            elif any(p["name"].lower() == clean_name.lower() for p in data["players"]):
                st.error(f"'{clean_name}' ist bereits registriert.")
            else:
                photo_path = None
                if new_photo is not None:
                    file_ext = os.path.splitext(new_photo.name)[1]
                    safe_name = "".join(c for c in clean_name if c.isalnum()) or "spieler"
                    unique_filename = f"{safe_name}_{uuid.uuid4().hex[:8]}{file_ext}"
                    photo_path = os.path.join(PHOTOS_DIR, unique_filename)
                    with open(photo_path, "wb") as f:
                        f.write(new_photo.getbuffer())

                new_player_id = str(uuid.uuid4())
                registration_timestamp = datetime.now().isoformat()
                registration_date_str = registration_timestamp[:10]

                new_player = {
                    "id": new_player_id,
                    "name": clean_name,
                    "birthdate": new_birthdate.isoformat(),
                    "photo": photo_path,
                    "active": True,
                    "is_trainer": is_trainer_checkbox,
                    "registered_at": registration_timestamp
                }
                data["players"].append(new_player)

                added_to_trainings = 0
                if not is_trainer_checkbox:
                    # Automatisch zu allen Trainings ab dem Registrierungsdatum hinzufügen
                    for t in data["trainings"]:
                        if t["date"] >= registration_date_str and new_player_id not in t["attendance"]:
                            t["attendance"][new_player_id] = {"status": "Anwesend", "points": 0}
                            added_to_trainings += 1

                save_data(data)

                if is_trainer_checkbox:
                    st.success(f"🎓 {clean_name} wurde als Trainer/Betreuer registriert.")
                else:
                    st.success(
                        f"🎉 {clean_name} wurde erfolgreich registriert und automatisch zu "
                        f"{added_to_trainings} anstehenden Trainingsterminen hinzugefügt!"
                    )
                st.rerun()

    st.markdown("---")
    st.subheader("Registrierte Spieler")

    if not data["players"]:
        st.info("Noch keine Spieler registriert.")
    else:
        header_cols = st.columns([1, 3, 2, 2, 2])
        header_cols[1].markdown("**Name**")
        header_cols[2].markdown("**Geburtsdatum**")
        header_cols[3].markdown("**Rolle**")
        header_cols[4].markdown("**Status**")
        st.markdown("---")

        for player in sorted(data["players"], key=lambda p: p["name"]):
            row_cols = st.columns([1, 3, 2, 2, 2])
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
                st.write("🎓 Trainer" if player.get("is_trainer", False) else "🏃 Spieler")
            with row_cols[4]:
                if st.session_state.is_admin:
                    is_active = st.checkbox(
                        "Aktiv",
                        value=player.get("active", True),
                        key=f"active_toggle_{player['id']}"
                    )
                    if is_active != player.get("active", True):
                        player["active"] = is_active
                        save_data(data)
                        st.rerun()
                else:
                    st.write("🟢 Aktiv" if player.get("active", True) else "⚪ Inaktiv")

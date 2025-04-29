import re
import streamlit as st
import os
import json
import uuid
import random
import pandas as pd
import glob
import sqlite3
from datetime import datetime


# --------------------------------------------------
# Authentication Setup
# --------------------------------------------------
import yaml
import streamlit as st
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader
from streamlit_authenticator.utilities.hasher import Hasher

passwords = ['abc', 'def']
hashed_passwords = Hasher.hash_list(passwords)

# Load your YAML config
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

# Hash any plain-text passwords in place
config["credentials"]["usernames"] = Hasher.hash_passwords(
    config["credentials"]["usernames"]
) 

# Initialize the authenticator with hashed passwords
authenticator = stauth.Authenticate(
    credentials        = config["credentials"],
    cookie_name        = config["cookie"]["name"],
    key                = config["cookie"]["key"],
    cookie_expiry_days = config["cookie"]["expiry_days"],
    preauthorized      = config.get("preauthorized")
)

# Render the login widget
name, authentication_status, username = authenticator.login("Login", "sidebar")
if authentication_status:
    authenticator.logout('Logout', 'main')
    st.write(f'Welcome *{name}*')
    st.title('Some content')
elif authentication_status == False:
    st.error('Username/password is incorrect')
elif authentication_status == None:
    st.warning('Please enter your username and password')

# --------------------------------------------------
# 0. Database Setup for Queryable Logs
# --------------------------------------------------
DB_DIR = "logs"
DB_PATH = os.path.join(DB_DIR, "logs.db")

def get_db_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS progress_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT,
      category TEXT,
      progress_json TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS annotations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      case_id TEXT,
      annotations_json TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------
# Helper: Prevent Duplicate SQLite Inserts
# --------------------------------------------------
def should_log(session_id: str, category: str, new_progress: dict) -> bool:
    """
    Skip logging if the latest saved entry for this session/category
    has the same last_case (for evals) or same case_id (for AI-edit).
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT progress_json FROM progress_logs "
        "WHERE session_id=? AND category=? "
        "ORDER BY timestamp DESC LIMIT 1",
        (session_id, category)
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return True
    last = json.loads(row[0])
    if "last_case" in new_progress:
        return last.get("last_case") != new_progress.get("last_case")
    if category == "ai_edit" and "case_id" in new_progress:
        return last.get("case_id") != new_progress.get("case_id")
    return True

# --------------------------------------------------
# 1. Generate & Store Unique Session ID
# --------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --------------------------------------------------
# 2. Sidebar: Display Session ID
# --------------------------------------------------
st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id}`")

# --------------------------------------------------
# 3. Utility: Save Progress per Category & Session
# --------------------------------------------------
def save_progress(category: str, progress: dict):
    sid = st.session_state.session_id
    if not should_log(sid, category, progress):
        return

    # JSON
    os.makedirs(DB_DIR, exist_ok=True)
    jpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.json")
    if os.path.exists(jpath):
        with open(jpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
    else:
        data = []
    data.append(progress)
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # CSV
    cpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.csv")
    df = pd.DataFrame([progress])
    if os.path.exists(cpath):
        df.to_csv(cpath, index=False, mode="a", header=False)
    else:
        df.to_csv(cpath, index=False)

    # SQLite
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO progress_logs(session_id, category, progress_json) VALUES (?, ?, ?)",
        (sid, category, json.dumps(progress))
    )
    conn.commit()
    conn.close()

# --------------------------------------------------
# 4. Utility: Save Annotations per Case
# --------------------------------------------------
def save_annotations(case_id: str, annotations: list):
    os.makedirs("evaluations", exist_ok=True)
    path = os.path.join("evaluations", f"{case_id}_annotations.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
    else:
        data = []
    data.extend(annotations)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO annotations(case_id, annotations_json) VALUES (?, ?)",
        (case_id, json.dumps(annotations))
    )
    conn.commit()
    conn.close()

# --------------------------------------------------
# 5. Initialize per-workflow Session State
# --------------------------------------------------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# Turing Test
init_state("last_case_turing", 0)
init_state("current_slice_turing", 0)
init_state("assignments_turing", {})
init_state("initial_eval_turing", None)
init_state("final_eval_turing", None)
init_state("viewed_images_turing", False)

# Standard Evaluation
init_state("last_case_standard", 0)
init_state("current_slice_standard", 0)
init_state("assignments_standard", {})
init_state("corrections_standard", [])

# AI Edit
init_state("last_case_ai", 0)
init_state("current_slice_ai", 0)
init_state("corrections_ai", [])
init_state("assembled_ai", "")

# --------------------------------------------------
# 6. Routing Setup
# --------------------------------------------------
params = st.experimental_get_query_params()
if "page" in params:
    st.session_state.page = params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

BASE_IMAGE_DIR = "2D_Image_clean"
cases = sorted([d for d in os.listdir(BASE_IMAGE_DIR) if os.path.isdir(os.path.join(BASE_IMAGE_DIR, d))])
total_cases = len(cases)

# --------------------------------------------------
# 7. Helpers for Text & Carousel
# --------------------------------------------------
def load_text(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

def display_carousel(category, case_id):
    key = f"current_slice_{category}"
    folder = os.path.join(BASE_IMAGE_DIR, case_id)
    if not os.path.exists(folder):
        st.info("No images.")
        return
    images = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    if not images:
        st.info("No images.")
        return

    idx = st.session_state[key]
    idx = max(0, min(idx, len(images)-1))
    st.session_state[key] = idx

    c1, c2, c3 = st.columns([1,8,1])
    with c1:
        if st.button("⟨ Prev", key=f"prev_{category}_{case_id}") and idx>0:
            st.session_state[key] -= 1; st.rerun()
    with c2:
        st.image(images[idx], width=500)
        st.caption(f"Slice {idx+1}/{len(images)}")
    with c3:
        if st.button("Next ⟩", key=f"next_{category}_{case_id}") and idx<len(images)-1:
            st.session_state[key] += 1; st.rerun()

# --------------------------------------------------
# 8. Pages
# --------------------------------------------------
def index():
    st.title("Survey App")
    if total_cases == 0:
        st.error("No cases found."); return
    st.markdown("### Your Progress")
    st.markdown(f"- **Turing Test**: Case {st.session_state.last_case_turing+1}/{total_cases}")
    st.markdown(f"- **Standard Eval**: Case {st.session_state.last_case_standard+1}/{total_cases}")
    st.markdown(f"- **AI Edit**: Case {st.session_state.last_case_ai+1}/{total_cases}")
    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    if c1.button("Turing Test"):
        st.experimental_set_query_params(page="turing_test"); st.session_state.page="turing_test"; st.rerun()
    if c2.button("Standard Eval"):
        st.experimental_set_query_params(page="standard_eval"); st.session_state.page="standard_eval"; st.rerun()
    if c3.button("AI Report Edit"):
        st.experimental_set_query_params(page="ai_edit"); st.session_state.page="ai_edit"; st.rerun()
    if c4.button("View All Results"):
        st.experimental_set_query_params(page="view_results"); st.session_state.page="view_results"; st.rerun()

def turing_test():
    idx = st.session_state.last_case_turing
    if idx >= total_cases:
        st.success("Turing Test complete!")
        if st.button("Home"):
            st.session_state.page="index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"Turing Test: {case} ({idx+1}/{total_cases})")

    # Save & Back now only navigates back—no logging
    if st.button("Save & Back"):
        st.session_state.page="index"
        st.experimental_set_query_params(page="index")
        st.rerun()

    gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
    ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    assigns = st.session_state.assignments_turing
    if case not in assigns:
        assigns[case] = random.choice([True, False])
        st.session_state.assignments_turing = assigns
    A,B = (ai,gt) if assigns[case] else (gt,ai)
    st.subheader("Report A"); st.text_area("A", A, height=200, key=f"A_t_{case}")
    st.subheader("Report B"); st.text_area("B", B, height=200, key=f"B_t_{case}")

    if st.session_state.initial_eval_turing is None:
        choice = st.radio("Which is GT?", ["A","B","Not sure"], key=f"ch_t_{case}", index=2)
        if st.button("Submit Initial"):
            st.session_state.initial_eval_turing = choice
            st.session_state.viewed_images_turing = True
            st.success("Recorded initial eval."); st.rerun()

    if st.session_state.viewed_images_turing:
        st.markdown("#### Images"); display_carousel("turing", case)
        st.markdown(f"**Initial Eval:** {st.session_state.initial_eval_turing}")
        up = st.radio("Keep or Update?", ["Keep","Update"], key=f"up_t_{case}")
        final = st.session_state.initial_eval_turing
        if up == "Update":
            final = st.radio("New choice:", ["A","B","Not sure"], key=f"new_t_{case}", index=2)
        st.session_state.final_eval_turing = final

        # Finalize & Next records progress and advances
        if st.button("Finalize & Next"):
            prog = {
                "case_id": case,
                "last_case": idx,
                "assignments": st.session_state.assignments_turing,
                "initial_eval": st.session_state.initial_eval_turing,
                "final_eval": st.session_state.final_eval_turing,
                "viewed_images": st.session_state.viewed_images_turing
            }
            save_progress("turing_test", prog)
            st.session_state.last_case_turing += 1
            st.session_state.current_slice_turing = 0
            st.session_state.initial_eval_turing = None
            st.session_state.final_eval_turing = None
            st.session_state.viewed_images_turing = False
            st.rerun()

def evaluate_case():
    idx = st.session_state.last_case_standard
    if idx >= total_cases:
        st.success("Standard Eval complete!")
        if st.button("Home"):
            st.session_state.page="index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"Standard Eval: {case} ({idx+1}/{total_cases})")

    # Save & Back now only navigates back—no logging
    if st.button("Save & Back"):
        st.session_state.page="index"
        st.experimental_set_query_params(page="index")
        st.rerun()

    gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
    ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    assigns = st.session_state.assignments_standard
    if case not in assigns:
        assigns[case] = random.choice([True, False])
        st.session_state.assignments_standard = assigns
    A,B = (ai,gt) if assigns[case] else (gt,ai)
    st.subheader("Report A"); st.text_area("A", A, height=150, key=f"A_s_{case}")
    st.subheader("Report B"); st.text_area("B", B, height=150, key=f"B_s_{case}")
    st.markdown("#### Images"); display_carousel("standard", case)

    organ = st.selectbox("Organ", [""] + ["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_s_{case}")
    reason = st.text_input("Reason", key=f"rsn_s_{case}")
    details = st.text_area("Details", key=f"dtl_s_{case}")
    if st.button("Add Corr") and organ:
        st.session_state.corrections_standard.append({
            "case_id": case, "organ": organ, "reason": reason, "details": details
        })
        st.success("Added correction"); st.rerun()

    cors = [c for c in st.session_state.corrections_standard if c["case_id"] == case]
    if cors:
        st.table(pd.DataFrame(cors).drop(columns=["case_id"]))

    choice = st.radio("Best report?", ["A","B","Corrected","Equal"], key=f"ch_s_{case}")
    if st.button("Submit & Next"):
        if cors:
            save_annotations(case, cors)
        # Log final standard-eval progress here
        prog = {
            "case_id": case,
            "last_case": idx,
            "assignments": st.session_state.assignments_standard,
            "corrections": st.session_state.corrections_standard
        }
        save_progress("standard_evaluation", prog)
        st.session_state.corrections_standard = [
            c for c in st.session_state.corrections_standard if c["case_id"] != case
        ]
        st.session_state.last_case_standard += 1
        st.session_state.current_slice_standard = 0
        st.rerun()

def ai_edit():
    idx = st.session_state.last_case_ai
    if idx >= total_cases:
        st.success("AI Edit complete!")
        if st.button("Home"):
            st.session_state.page="index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"AI Edit: {case} ({idx+1}/{total_cases})")

    # -- Save & Back logs current work --
    if st.button("Save & Back"):
        prog = {
            "case_id": case,
            "mode": st.session_state.get("last_mode_ai", "Free"),
            "assembled": st.session_state.assembled_ai,
            "corrections": st.session_state.corrections_ai
        }
        save_progress("ai_edit", prog)
        st.session_state.page="index"; st.experimental_set_query_params(page="index"); st.rerun()

    orig = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    st.subheader("Original AI Report")
    st.text_area("orig", orig, height=150, disabled=True)
    st.markdown("#### Images"); display_carousel("ai", case)

    mode = st.radio("Mode", ["Free","Organ"], key=f"md_ai_{case}")
    st.session_state["last_mode_ai"] = mode

    if mode == "Free":
        text = st.session_state.assembled_ai or orig
        new = st.text_area("Edit", text, height=200, key=f"free_ai_{case}")
        st.session_state.assembled_ai = new
    else:
        organ = st.selectbox("Organ", [""]+["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_ai_{case}")
        reason = st.text_input("Reason", key=f"rsn_ai_{case}")
        details = st.text_area("Details", key=f"dtl_ai_{case}")
        if st.button("Add Corr AI") and organ:
            st.session_state.corrections_ai.append({
                "case_id": case, "organ": organ, "reason": reason, "details": details
            })
            st.success("Added"); st.rerun()

        cors = [c for c in st.session_state.corrections_ai if c["case_id"] == case]
        if cors:
            st.table(pd.DataFrame(cors).drop(columns=["case_id"]))
            if st.button("Assemble"):
                txt = "\n".join(f"- {c['organ']}: {c['reason']} — {c['details']}" for c in cors)
                st.session_state.assembled_ai = txt
                st.success("Assembled"); st.rerun()

    if st.button("Submit & Next"):
        prog = {
            "case_id": case,
            "mode": mode,
            "assembled": st.session_state.assembled_ai,
            "corrections": st.session_state.corrections_ai
        }
        save_progress("ai_edit", prog)
        st.session_state.corrections_ai = [c for c in st.session_state.corrections_ai if c["case_id"] != case]
        st.session_state.assembled_ai = ""
        st.session_state.last_case_ai += 1
        st.session_state.current_slice_ai = 0
        st.rerun()

def view_all_results():
    st.title("All Saved Results")
    if st.button("Home"):
        st.session_state.page="index"; st.experimental_set_query_params(page="index"); st.rerun()

    conn = get_db_connection()

    # Sessions
    df_sessions = pd.read_sql_query(
        "SELECT DISTINCT session_id FROM progress_logs ORDER BY session_id", conn
    )
    st.subheader("All Sessions with Saved Progress")
    for sid in df_sessions["session_id"]:
        st.write(f"- {sid}")

    # Turing & Standard
    for cat,label in [
        ("turing_test","Turing Test Logs"),
        ("standard_evaluation","Standard Eval Logs")
    ]:
        st.subheader(label)
        df = pd.read_sql_query(
            "SELECT session_id, progress_json, timestamp FROM progress_logs WHERE category=? ORDER BY timestamp",
            conn, params=(cat,)
        )
        if not df.empty:
            df_expanded = pd.concat([
                df.drop(columns=["progress_json"]),
                df["progress_json"].apply(json.loads).apply(pd.Series)
            ], axis=1)
            for col in df_expanded.columns:
                if df_expanded[col].apply(lambda x: isinstance(x, (dict,list))).any():
                    df_expanded[col] = df_expanded[col].apply(json.dumps)
            if "last_case" in df_expanded.columns:
                df_expanded["Case"] = df_expanded["last_case"] + 1
                df_expanded = df_expanded.drop(columns=["last_case"])
                cols = ["Case"] + [c for c in df_expanded.columns if c!="Case"]
                st.dataframe(df_expanded[cols])
            else:
                st.dataframe(df_expanded)
        else:
            st.write("— no entries —")

    # AI Report Edit Logs
    st.subheader("AI Report Edit Logs")
    df_ai = pd.read_sql_query(
        "SELECT session_id, progress_json, timestamp FROM progress_logs WHERE category='ai_edit' ORDER BY timestamp", conn
    )
    if not df_ai.empty:
        df_ai_expanded = pd.concat([
            df_ai.drop(columns=["progress_json"]),
            df_ai["progress_json"].apply(json.loads).apply(pd.Series)
        ], axis=1)
        for col in df_ai_expanded.columns:
            if df_ai_expanded[col].apply(lambda x: isinstance(x, (dict,list))).any():
                df_ai_expanded[col] = df_ai_expanded[col].apply(json.dumps)
        st.dataframe(df_ai_expanded)
    else:
        st.write("— no AI edit logs found —")

    conn.close()

# --------------------------------------------------
# 9. Main Router
# --------------------------------------------------
page = st.session_state.page
if page=="turing_test":
    turing_test()
elif page=="standard_eval":
    evaluate_case()
elif page=="ai_edit":
    ai_edit()
elif page=="view_results":
    view_all_results()
else:
    index()

# import re
# import os
# import json
# import random
# import sqlite3
# from datetime import datetime

# import streamlit as st
# import pandas as pd
# import streamlit_authenticator as stauth
# import yaml
# from yaml.loader import SafeLoader
# from streamlit_authenticator.utilities.hasher import Hasher

# # ─── For unique session IDs ────────────────────────────────────────────────────
# from streamlit.runtime import get_instance
# from streamlit.runtime.scriptrunner import get_script_run_ctx

# # ─── 0. Authentication Setup ───────────────────────────────────────────────────
# with open("config.yaml") as file:
#     config = yaml.load(file, Loader=SafeLoader)

# if "credentials" not in config or "usernames" not in config["credentials"]:
#     st.error("❌ Your config.yaml must include a 'credentials → usernames' section.")
#     st.stop()

# config["credentials"] = Hasher.hash_passwords(config["credentials"])
# authenticator = stauth.Authenticate(
#     credentials        = config["credentials"],
#     cookie_name        = config["cookie"]["name"],
#     key                = config["cookie"]["key"],
#     cookie_expiry_days = config["cookie"]["expiry_days"],
#     preauthorized      = config.get("preauthorized", [])
# )
# authenticator.login(location="sidebar", key="login")

# name                  = st.session_state.get("name")
# authentication_status = st.session_state.get("authentication_status")
# username              = st.session_state.get("username")
# if not authentication_status:
#     if authentication_status is False:
#         st.error("❌ Username/password is incorrect")
#     else:
#         st.warning("⚠️ Please enter your username and password")
#     st.stop()

# # ─── 1. Generate a Unique Session ID ────────────────────────────────────────────
# def get_unique_user_session():
#     ctx = get_script_run_ctx()
#     if ctx is None:
#         return username
#     raw_id = ctx.session_id
#     try:
#         # verify existence in session manager (Streamlit ≥1.30)
#         if get_instance()._session_mgr.get_session_info(raw_id) is None:
#             raise RuntimeError()
#     except Exception:
#         pass
#     return raw_id

# unique_sid = get_unique_user_session()
# st.session_state.session_id = f"{username}_{unique_sid}"
# st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id}`")

# # ─── 2. Database Init & Helpers ─────────────────────────────────────────────────
# DB_DIR = os.path.join(os.getcwd(), "db")
# DB_PATH = os.path.join(DB_DIR, "progress.db")

# def get_db_connection():
#     os.makedirs(DB_DIR, exist_ok=True)
#     return sqlite3.connect(DB_PATH, check_same_thread=False)

# def init_db():
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS progress_logs (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             session_id TEXT NOT NULL,
#             category TEXT NOT NULL,
#             progress_json TEXT NOT NULL,
#             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS annotations (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             case_id TEXT NOT NULL,
#             annotations_json TEXT NOT NULL,
#             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#     conn.commit()
#     conn.close()

# init_db()

# def should_log(session_id: str, category: str, new_prog: dict) -> bool:
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "SELECT progress_json FROM progress_logs "
#         "WHERE session_id=? AND category=? "
#         "ORDER BY timestamp DESC LIMIT 1",
#         (session_id, category)
#     )
#     row = c.fetchone()
#     conn.close()
#     if not row:
#         return True
#     last = json.loads(row[0])
#     if "last_case" in new_prog:
#         return last.get("last_case") != new_prog.get("last_case")
#     if category == "ai_edit" and "case_id" in new_prog:
#         return last.get("case_id") != new_prog.get("case_id")
#     return True

# def save_progress(category: str, progress: dict):
#     sid = st.session_state.session_id
#     if not should_log(sid, category, progress):
#         return
#     # JSON
#     os.makedirs(DB_DIR, exist_ok=True)
#     jpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.json")
#     if os.path.exists(jpath):
#         with open(jpath, "r", encoding="utf-8") as f:
#             data = json.load(f)
#             data = data if isinstance(data, list) else [data]
#     else:
#         data = []
#     data.append(progress)
#     with open(jpath, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)
#     # CSV
#     cpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.csv")
#     df = pd.DataFrame([progress])
#     if os.path.exists(cpath):
#         df.to_csv(cpath, index=False, mode="a", header=False)
#     else:
#         df.to_csv(cpath, index=False)
#     # SQLite
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "INSERT INTO progress_logs(session_id, category, progress_json) VALUES (?, ?, ?)",
#         (sid, category, json.dumps(progress))
#     )
#     conn.commit()
#     conn.close()

# def save_annotations(case_id: str, annotations: list):
#     os.makedirs("evaluations", exist_ok=True)
#     path = os.path.join("evaluations", f"{case_id}_annotations.json")
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#             data = data if isinstance(data, list) else [data]
#     else:
#         data = []
#     data.extend(annotations)
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "INSERT INTO annotations(case_id, annotations_json) VALUES (?, ?)",
#         (case_id, json.dumps(annotations))
#     )
#     conn.commit()
#     conn.close()

# # ─── 3. Save Progress on Logout ─────────────────────────────────────────────────
# def save_all_progress(_=None):
#     if (st.session_state.initial_eval_turing is not None
#         or st.session_state.viewed_images_turing):
#         prog = {
#             "case_id":      st.session_state.last_case_turing,
#             "last_case":    st.session_state.last_case_turing,
#             "assignments":  st.session_state.assignments_turing,
#             "initial_eval": st.session_state.initial_eval_turing,
#             "final_eval":   st.session_state.final_eval_turing,
#             "viewed_images":st.session_state.viewed_images_turing,
#         }
#         save_progress("turing_test", prog)

#     if st.session_state.corrections_standard:
#         prog = {
#             "case_id":     st.session_state.last_case_standard,
#             "last_case":   st.session_state.last_case_standard,
#             "assignments": st.session_state.assignments_standard,
#             "corrections": st.session_state.corrections_standard,
#         }
#         save_progress("standard_evaluation", prog)

#     if (st.session_state.assembled_ai
#         or st.session_state.corrections_ai):
#         prog = {
#             "case_id":    st.session_state.last_case_ai,
#             "mode":       st.session_state.get("last_mode_ai", "Free"),
#             "assembled":  st.session_state.assembled_ai,
#             "corrections":st.session_state.corrections_ai,
#         }
#         save_progress("ai_edit", prog)

# # ─── 4. Single Logout Button with Unique Key ────────────────────────────────────
# logout_key = f"auth_logout_{st.session_state.session_id}"
# authenticator.logout(
#     location="sidebar",
#     key=logout_key,
#     callback=save_all_progress
# )


# # --------------------------------------------------
# # 1. Session ID per user (persist across logins)
# # --------------------------------------------------
# # Use the authenticated username so progress persists across sessions
# st.session_state.session_id = username  # ← CHANGED
# st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id}`")

# # --------------------------------------------------
# # 2. Database Setup for Queryable Logs
# # --------------------------------------------------
# DB_DIR = "logs"
# DB_PATH = os.path.join(DB_DIR, "logs.db")

# def get_db_connection():
#     os.makedirs(DB_DIR, exist_ok=True)
#     return sqlite3.connect(DB_PATH, check_same_thread=False)

# def init_db():
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute('''
#     CREATE TABLE IF NOT EXISTS progress_logs (
#       id INTEGER PRIMARY KEY AUTOINCREMENT,
#       session_id TEXT,
#       category TEXT,
#       progress_json TEXT,
#       timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#     )''')
#     c.execute('''
#     CREATE TABLE IF NOT EXISTS annotations (
#       id INTEGER PRIMARY KEY AUTOINCREMENT,
#       case_id TEXT,
#       annotations_json TEXT,
#       timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#     )''')
#     conn.commit()
#     conn.close()

# init_db()

# # --------------------------------------------------
# # 3. Load last saved 'last_case' from DB
# # --------------------------------------------------
# def load_last_progress(category: str) -> int:  # ← NEW
#     """
#     Return the last_case index for this user & category, or 0 if none.
#     """
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "SELECT progress_json FROM progress_logs "
#         "WHERE session_id=? AND category=? "
#         "ORDER BY timestamp DESC LIMIT 1",
#         (st.session_state.session_id, category)
#     )
#     row = c.fetchone()
#     conn.close()
#     if row:
#         data = json.loads(row[0])
#         return data.get("last_case", 0)
#     return 0

# # --------------------------------------------------
# # 4. Helper: Prevent Duplicate SQLite Inserts
# # --------------------------------------------------
# def should_log(session_id: str, category: str, new_progress: dict) -> bool:
#     """
#     Skip logging if the latest saved entry for this session/category
#     has the same last_case (for evals) or same case_id (for AI-edit).
#     """
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "SELECT progress_json FROM progress_logs "
#         "WHERE session_id=? AND category=? "
#         "ORDER BY timestamp DESC LIMIT 1",
#         (session_id, category)
#     )
#     row = c.fetchone()
#     conn.close()
#     if not row:
#         return True
#     last = json.loads(row[0])
#     if "last_case" in new_progress:
#         return last.get("last_case") != new_progress.get("last_case")
#     if category == "ai_edit" and "case_id" in new_progress:
#         return last.get("case_id") != new_progress.get("case_id")
#     return True

# # --------------------------------------------------
# # 5. Utilities to Save Progress & Annotations
# # --------------------------------------------------
# def save_progress(category: str, progress: dict):
#     sid = st.session_state.session_id
#     if not should_log(sid, category, progress):
#         return

#     # JSON file
#     os.makedirs(DB_DIR, exist_ok=True)
#     jpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.json")
#     if os.path.exists(jpath):
#         with open(jpath, "r", encoding="utf-8") as f:
#             data = json.load(f)
#             data = data if isinstance(data, list) else [data]
#     else:
#         data = []
#     data.append(progress)
#     with open(jpath, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)

#     # CSV file
#     cpath = os.path.join(DB_DIR, f"{category}_{sid}_progress.csv")
#     df = pd.DataFrame([progress])
#     if os.path.exists(cpath):
#         df.to_csv(cpath, index=False, mode="a", header=False)
#     else:
#         df.to_csv(cpath, index=False)

#     # SQLite
#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "INSERT INTO progress_logs(session_id, category, progress_json) VALUES (?, ?, ?)",
#         (sid, category, json.dumps(progress))
#     )
#     conn.commit()
#     conn.close()

# def save_annotations(case_id: str, annotations: list):
#     os.makedirs("evaluations", exist_ok=True)
#     path = os.path.join("evaluations", f"{case_id}_annotations.json")
#     if os.path.exists(path):
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#             data = data if isinstance(data, list) else [data]
#     else:
#         data = []
#     data.extend(annotations)
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(data, f, indent=2)

#     conn = get_db_connection()
#     c = conn.cursor()
#     c.execute(
#         "INSERT INTO annotations(case_id, annotations_json) VALUES (?, ?)",
#         (case_id, json.dumps(annotations))
#     )
#     conn.commit()
#     conn.close()

# # --------------------------------------------------
# # 6. Initialize per-workflow Session State
# # --------------------------------------------------
# def init_state(key, default):
#     if key not in st.session_state:
#         st.session_state[key] = default

# # Seed last_case_* from database so user can resume
# init_state("last_case_turing",    load_last_progress("turing_test"))        # ← CHANGED
# init_state("current_slice_turing", 0)
# init_state("assignments_turing",   {})
# init_state("initial_eval_turing",  None)
# init_state("final_eval_turing",    None)
# init_state("viewed_images_turing", False)

# init_state("last_case_standard",   load_last_progress("standard_evaluation")) # ← CHANGED
# init_state("current_slice_standard", 0)
# init_state("assignments_standard",   {})
# init_state("corrections_standard",   [])

# init_state("last_case_ai",         load_last_progress("ai_edit"))           # ← CHANGED
# init_state("current_slice_ai",       0)
# init_state("corrections_ai",         [])
# init_state("assembled_ai",          "")

# # --------------------------------------------------
# # 7. Routing Setup & Helpers
# # --------------------------------------------------
# # Ensure a default page is set once
# if "page" not in st.session_state:
#     st.session_state.page = "index"

# BASE_IMAGE_DIR = "2D_Image_clean"
# cases = sorted([
#     d for d in os.listdir(BASE_IMAGE_DIR)
#     if os.path.isdir(os.path.join(BASE_IMAGE_DIR, d))
# ])
# total_cases = len(cases)

# def load_text(path):
#     return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

# def display_carousel(category, case_id):
#     key = f"current_slice_{category}"
#     folder = os.path.join(BASE_IMAGE_DIR, case_id)
#     if not os.path.exists(folder):
#         st.info("No images.")
#         return
#     images = sorted([
#         os.path.join(folder, f)
#         for f in os.listdir(folder)
#         if f.lower().endswith((".png", ".jpg", ".jpeg"))
#     ])
#     if not images:
#         st.info("No images.")
#         return

#     idx = st.session_state[key]
#     idx = max(0, min(idx, len(images)-1))
#     st.session_state[key] = idx

#     c1, c2, c3 = st.columns([1,8,1])
#     with c1:
#         if st.button("⟨ Prev", key=f"prev_{category}_{case_id}") and idx > 0:
#             st.session_state[key] -= 1
#             st.rerun()
#     with c2:
#         st.image(images[idx], width=500)
#         st.caption(f"Slice {idx+1}/{len(images)}")
#     with c3:
#         if st.button("Next ⟩", key=f"next_{category}_{case_id}") and idx < len(images)-1:
#             st.session_state[key] += 1
#             st.rerun()

# # --------------------------------------------------
# # 8. Pages
# # --------------------------------------------------
# def index():
#     st.title("Survey App")
#     if total_cases == 0:
#         st.error("No cases found.")
#         return

#     st.markdown("### Your Progress")
#     st.markdown(f"- **Turing Test**: Case {st.session_state.last_case_turing+1}/{total_cases}")
#     st.markdown(f"- **Standard Eval**: Case {st.session_state.last_case_standard+1}/{total_cases}")
#     st.markdown(f"- **AI Edit**: Case {st.session_state.last_case_ai+1}/{total_cases}")
#     st.markdown("---")

#     c1, c2, c3, c4 = st.columns(4)
#     if c1.button("Turing Test"):
#         st.session_state.page = "turing_test"
#         st.rerun()
#     if c2.button("Standard Eval"):
#         st.session_state.page = "standard_eval"
#         st.rerun()
#     if c3.button("AI Report Edit"):
#         st.session_state.page = "ai_edit"
#         st.rerun()
#     if c4.button("View All Results"):
#         st.session_state.page = "view_results"
#         st.rerun()

# def turing_test():
#     idx = st.session_state.last_case_turing
#     # If we're past the last case, show completion and let user go Home
#     if idx >= total_cases:
#         st.success("Turing Test complete!")
#         if st.button("Home"):
#             st.session_state.page = "index"
#             st.rerun()
#         return

#     case = cases[idx]
#     st.header(f"Turing Test: {case} ({idx+1}/{total_cases})")

#     if st.button("Save & Back"):
#         st.session_state.page = "index"
#         st.rerun()

#     gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
#     ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
#     assigns = st.session_state.assignments_turing
#     if case not in assigns:
#         assigns[case] = random.choice([True, False])
#         st.session_state.assignments_turing = assigns
#     A, B = (ai, gt) if assigns[case] else (gt, ai)

#     st.subheader("Report A")
#     st.text_area("A", A, height=200, key=f"A_t_{case}")
#     st.subheader("Report B")
#     st.text_area("B", B, height=200, key=f"B_t_{case}")

#     if st.session_state.initial_eval_turing is None:
#         choice = st.radio("Which is GT?", ["A","B","Not sure"], key=f"ch_t_{case}", index=2)
#         if st.button("Submit Initial"):
#             st.session_state.initial_eval_turing = choice
#             st.session_state.viewed_images_turing = True
#             st.success("Recorded initial eval.")
#             st.rerun()

#     if st.session_state.viewed_images_turing:
#         st.markdown("#### Images")
#         display_carousel("turing", case)
#         st.markdown(f"**Initial Eval:** {st.session_state.initial_eval_turing}")

#         up = st.radio("Keep or Update?", ["Keep","Update"], key=f"up_t_{case}")
#         final = st.session_state.initial_eval_turing
#         if up == "Update":
#             final = st.radio("New choice:", ["A","B","Not sure"], key=f"new_t_{case}", index=2)
#         st.session_state.final_eval_turing = final

#         if st.button("Finalize & Next"):
#             prog = {
#                 "case_id": case,
#                 "last_case": idx,
#                 "assignments": st.session_state.assignments_turing,
#                 "initial_eval": st.session_state.initial_eval_turing,
#                 "final_eval": st.session_state.final_eval_turing,
#                 "viewed_images": st.session_state.viewed_images_turing
#             }
#             save_progress("turing_test", prog)
#             st.session_state.last_case_turing += 1
#             st.session_state.current_slice_turing = 0
#             st.session_state.initial_eval_turing = None
#             st.session_state.final_eval_turing = None
#             st.session_state.viewed_images_turing = False
#             st.rerun()

# def evaluate_case():
#     idx = st.session_state.last_case_standard
#     if idx >= total_cases:
#         st.success("Standard Eval complete!")
#         if st.button("Home"):
#             st.session_state.page = "index"
#             st.rerun()
#         return

#     case = cases[idx]
#     st.header(f"Standard Eval: {case} ({idx+1}/{total_cases})")

#     if st.button("Save & Back"):
#         st.session_state.page = "index"
#         st.rerun()

#     gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
#     ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
#     assigns = st.session_state.assignments_standard
#     if case not in assigns:
#         assigns[case] = random.choice([True, False])
#         st.session_state.assignments_standard = assigns
#     A, B = (ai, gt) if assigns[case] else (gt, ai)

#     st.subheader("Report A")
#     st.text_area("A", A, height=150, key=f"A_s_{case}")
#     st.subheader("Report B")
#     st.text_area("B", B, height=150, key=f"B_s_{case}")

#     st.markdown("#### Images")
#     display_carousel("standard", case)

#     organ = st.selectbox("Organ", [""] + ["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_s_{case}")
#     reason = st.text_input("Reason", key=f"rsn_s_{case}")
#     details = st.text_area("Details", key=f"dtl_s_{case}")

#     if st.button("Add Corr") and organ:
#         st.session_state.corrections_standard.append({
#             "case_id": case,
#             "organ": organ,
#             "reason": reason,
#             "details": details
#         })
#         st.success("Added correction")
#         st.rerun()

#     cors = [c for c in st.session_state.corrections_standard if c["case_id"] == case]
#     if cors:
#         st.table(pd.DataFrame(cors).drop(columns=["case_id"]))

#     choice = st.radio("Best report?", ["A","B","Corrected","Equal"], key=f"ch_s_{case}")
#     if st.button("Submit & Next"):
#         if cors:
#             save_annotations(case, cors)
#         prog = {
#             "case_id": case,
#             "last_case": idx,
#             "assignments": st.session_state.assignments_standard,
#             "corrections": st.session_state.corrections_standard
#         }
#         save_progress("standard_evaluation", prog)
#         st.session_state.corrections_standard = [
#             c for c in st.session_state.corrections_standard if c["case_id"] != case
#         ]
#         st.session_state.last_case_standard += 1
#         st.session_state.current_slice_standard = 0
#         st.rerun()

# def ai_edit():
#     idx = st.session_state.last_case_ai
#     if idx >= total_cases:
#         st.success("AI Edit complete!")
#         if st.button("Home"):
#             st.session_state.page = "index"
#             st.rerun()
#         return

#     case = cases[idx]
#     st.header(f"AI Edit: {case} ({idx+1}/{total_cases})")

#     if st.button("Save & Back"):
#         prog = {
#             "case_id": case,
#             "mode": st.session_state.get("last_mode_ai", "Free"),
#             "assembled": st.session_state.assembled_ai,
#             "corrections": st.session_state.corrections_ai
#         }
#         save_progress("ai_edit", prog)
#         st.session_state.page = "index"
#         st.rerun()

#     orig = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
#     st.subheader("Original AI Report")
#     st.text_area("orig", orig, height=150, disabled=True)

#     st.markdown("#### Images")
#     display_carousel("ai", case)

#     mode = st.radio("Mode", ["Free","Organ"], key=f"md_ai_{case}")
#     st.session_state["last_mode_ai"] = mode

#     if mode == "Free":
#         text = st.session_state.assembled_ai or orig
#         new = st.text_area("Edit", text, height=200, key=f"free_ai_{case}")
#         st.session_state.assembled_ai = new
#     else:
#         organ = st.selectbox("Organ", [""] + ["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_ai_{case}")
#         reason = st.text_input("Reason", key=f"rsn_ai_{case}")
#         details = st.text_area("Details", key=f"dtl_ai_{case}")
#         if st.button("Add Corr AI") and organ:
#             st.session_state.corrections_ai.append({
#                 "case_id": case,
#                 "organ": organ,
#                 "reason": reason,
#                 "details": details
#             })
#             st.success("Added")
#             st.rerun()

#         cors = [c for c in st.session_state.corrections_ai if c["case_id"] == case]
#         if cors:
#             st.table(pd.DataFrame(cors).drop(columns=["case_id"]))
#             if st.button("Assemble"):
#                 txt = "\n".join(f"- {c['organ']}: {c['reason']} — {c['details']}" for c in cors)
#                 st.session_state.assembled_ai = txt
#                 st.success("Assembled")
#                 st.rerun()

#     if st.button("Submit & Next"):
#         prog = {
#             "case_id": case,
#             "mode": mode,
#             "assembled": st.session_state.assembled_ai,
#             "corrections": st.session_state.corrections_ai
#         }
#         save_progress("ai_edit", prog)
#         st.session_state.corrections_ai = [
#             c for c in st.session_state.corrections_ai if c["case_id"] != case
#         ]
#         st.session_state.assembled_ai = ""
#         st.session_state.last_case_ai += 1
#         st.session_state.current_slice_ai = 0
#         st.rerun()

# def view_all_results():
#     st.title("All Saved Results")
#     if st.button("Home"):
#         st.session_state.page = "index"
#         st.rerun()

#     conn = get_db_connection()

#     # List all sessions
#     df_sessions = pd.read_sql_query(
#         "SELECT DISTINCT session_id FROM progress_logs ORDER BY session_id",
#         conn
#     )
#     st.subheader("All Sessions with Saved Progress")
#     for sid in df_sessions["session_id"]:
#         st.write(f"- {sid}")

#     # Turing & Standard logs
#     for cat,label in [
#         ("turing_test","Turing Test Logs"),
#         ("standard_evaluation","Standard Eval Logs")
#     ]:
#         st.subheader(label)
#         df = pd.read_sql_query(
#             "SELECT session_id, progress_json, timestamp FROM progress_logs WHERE category=? ORDER BY timestamp",
#             conn, params=(cat,)
#         )
#         if not df.empty:
#             df_expanded = pd.concat([
#                 df.drop(columns=["progress_json"]),
#                 df["progress_json"].apply(json.loads).apply(pd.Series)
#             ], axis=1)
#             for col in df_expanded.columns:
#                 if df_expanded[col].apply(lambda x: isinstance(x, (dict,list))).any():
#                     df_expanded[col] = df_expanded[col].apply(json.dumps)
#             if "last_case" in df_expanded.columns:
#                 df_expanded["Case"] = df_expanded["last_case"] + 1
#                 df_expanded = df_expanded.drop(columns=["last_case"])
#                 cols = ["Case"] + [c for c in df_expanded.columns if c!="Case"]
#                 st.dataframe(df_expanded[cols])
#             else:
#                 st.dataframe(df_expanded)
#         else:
#             st.write("— no entries —")

#     # AI Edit Logs
#     st.subheader("AI Report Edit Logs")
#     df_ai = pd.read_sql_query(
#         "SELECT session_id, progress_json, timestamp FROM progress_logs WHERE category='ai_edit' ORDER BY timestamp",
#         conn
#     )
#     if not df_ai.empty:
#         df_ai_expanded = pd.concat([
#             df_ai.drop(columns=["progress_json"]),
#             df_ai["progress_json"].apply(json.loads).apply(pd.Series)
#         ], axis=1)
#         for col in df_ai_expanded.columns:
#             if df_ai_expanded[col].apply(lambda x: isinstance(x, (dict,list))).any():
#                 df_ai_expanded[col] = df_ai_expanded[col].apply(json.dumps)
#         st.dataframe(df_ai_expanded)
#     else:
#         st.write("— no AI edit logs found —")

#     conn.close()

# # --------------------------------------------------
# # 9. Main Router
# # --------------------------------------------------
# page = st.session_state.page
# if page == "turing_test":
#     turing_test()
# elif page == "standard_eval":
#     evaluate_case()
# elif page == "ai_edit":
#     ai_edit()
# elif page == "view_results":
#     view_all_results()
# else:
#     index()





import streamlit as st
import sqlite3
import hashlib
import os
import glob
import csv
from datetime import datetime

# ─── Configuration ─────────────────────────────────────────────────────────────
BASE_IMAGE_DIR = "2D_Image_clean"
DB_PATH        = "turing_test.db"
LOGS_DIR       = "logs"

os.makedirs(LOGS_DIR, exist_ok=True)

# ─── Database Initialization ────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    # Users table (passwords are SHA-256 hashes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    # Results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            username    TEXT NOT NULL,
            case_folder TEXT NOT NULL,
            truth       TEXT NOT NULL,
            user_guess  TEXT NOT NULL,
            correct     INTEGER NOT NULL,
            timestamp   TEXT NOT NULL
        )
    """)
    conn.commit()
    # Seed demo users if none exist
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        demo = {"radiologist1": "password1", "radiologist2": "password2"}
        for user, pw in demo.items():
            pw_hash = hashlib.sha256(pw.encode()).hexdigest()
            c.execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                (user, pw_hash)
            )
        conn.commit()
    conn.close()

init_db()

# ─── Helper Functions ────────────────────────────────────────────────────────────
def check_credentials(username: str, password: str) -> bool:
    """Verify username/password against the users table."""
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur  = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0] == pw_hash)

def load_user_progress(username: str):
    """Return (list of completed folders, dict of details)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur  = conn.cursor()
    cur.execute("""
        SELECT case_folder, truth, user_guess, correct
        FROM results WHERE username=?
    """, (username,))
    rows = cur.fetchall()
    conn.close()
    completed = []
    prog = {}
    for folder, truth, guess, corr in rows:
        if folder not in completed:
            completed.append(folder)
        prog[folder] = {"truth": truth, "guess": guess, "correct": corr}
    return completed, prog

def save_result(username: str, folder: str, truth: str, guess: str, correct: int):
    """Persist a single Turing Test result."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # SQLite
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO results(username,case_folder,truth,user_guess,correct,timestamp)
        VALUES(?,?,?,?,?,?)
    """, (username, folder, truth, guess, correct, ts))
    conn.commit()
    conn.close()
    # CSV log
    log_path = os.path.join(LOGS_DIR, f"{username}_results.csv")
    write_header = not os.path.isfile(log_path)
    with open(log_path, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["username","case_folder","truth","user_guess","correct","timestamp"])
        w.writerow([username, folder, truth, guess, correct, ts])

def list_cases():
    """List all subfolders under BASE_IMAGE_DIR as case identifiers."""
    if not os.path.isdir(BASE_IMAGE_DIR):
        return []
    return sorted([
        d for d in os.listdir(BASE_IMAGE_DIR)
        if os.path.isdir(os.path.join(BASE_IMAGE_DIR, d))
    ])

def display_carousel(case_folder: str):
    """Show all images in BASE_IMAGE_DIR/case_folder with Prev/Next controls."""
    folder = os.path.join(BASE_IMAGE_DIR, case_folder)
    images = sorted([
        os.path.join(folder, fn)
        for fn in os.listdir(folder)
        if fn.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    if not images:
        st.info("No images found for this case.")
        return
    key = f"slice_{case_folder}"
    if key not in st.session_state:
        st.session_state[key] = 0
    idx = st.session_state[key]
    c1, c2, c3 = st.columns([1, 8, 1])
    with c1:
        if st.button("⟨ Prev", key=f"prev_{case_folder}") and idx > 0:
            st.session_state[key] -= 1
            st.rerun()
    with c2:
        st.image(images[idx], use_column_width=True)
        st.caption(f"Slice {idx+1}/{len(images)}")
    with c3:
        if st.button("Next ⟩", key=f"next_{case_folder}") and idx < len(images) - 1:
            st.session_state[key] += 1
            st.rerun()

# ─── Discover Cases ──────────────────────────────────────────────────────────────
cases       = list_cases()
total_cases = len(cases)

# ─── Session State Initialization ───────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in       = False
    st.session_state.username        = None
    st.session_state.completed_cases = []
    st.session_state.progress        = {}
    st.session_state.current_case    = None
    st.session_state.assignment      = {}

# ─── Sidebar: Login / Logout ─────────────────────────────────────────────────────
if st.session_state.logged_in:
    st.sidebar.write(f"**User:** {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
else:
    st.sidebar.header("Log in")
    user_in = st.sidebar.text_input("Username")
    pw_in   = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if check_credentials(user_in, pw_in):
            # Clear any old keys
            st.session_state.clear()
            # Set up new session
            st.session_state.logged_in       = True
            st.session_state.username        = user_in
            done, prog = load_user_progress(user_in)
            st.session_state.completed_cases = done
            st.session_state.progress        = prog
            # Next case to evaluate
            nxt = None
            for cf in cases:
                if cf not in done:
                    nxt = cf
                    break
            st.session_state.current_case = nxt
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")

# ─── Main: Turing Test ────────────────────────────────────────────────────────────
if st.session_state.logged_in:
    st.title("Turing Test")
    cf = st.session_state.current_case

    if cf is None:
        st.success("🎉 You've finished all cases. Thank you!")
    else:
        idx = cases.index(cf)
        st.header(f"Case: {cf} ({idx+1}/{total_cases})")

        # Assign ground truth once per folder
        ak = f"assign_{cf}"
        if ak not in st.session_state:
            import random
            st.session_state[ak] = random.choice(["AI", "Radiologist"])
        truth = st.session_state[ak]

        # Show images
        display_carousel(cf)

        # Collect guess
        guess_key = f"guess_{cf}"
        options   = ["Select...", "AI", "Radiologist"]
        if guess_key not in st.session_state:
            st.session_state[guess_key] = options[0]
        choice = st.radio(
            "This annotation was generated by:",
            options,
            index=options.index(st.session_state[guess_key]),
            key=guess_key
        )
        can_submit = choice != options[0]
        if st.button("Submit", disabled=not can_submit):
            if not can_submit:
                st.warning("Please select AI or Radiologist first.")
            else:
                correct = 1 if choice == truth else 0
                save_result(st.session_state.username, cf, truth, choice, correct)
                # Update progress
                st.session_state.completed_cases.append(cf)
                st.session_state.progress[cf] = {
                    "truth": truth, "guess": choice, "correct": correct
                }
                # Find next case
                nxt = None
                for cff in cases:
                    if cff not in st.session_state.completed_cases:
                        nxt = cff
                        break
                st.session_state.current_case = nxt
                # Reset the radio for next run
                st.session_state.pop(guess_key, None)
                # Also reset carousel index
                st.session_state.pop(f"slice_{cf}", None)
                st.rerun()

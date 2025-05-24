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

# Configuration
DB_PATH = "turing_test.db"
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR, exist_ok=True)

# Initialize SQLite database (create tables if not exist)
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT
    )
""")
c.execute("""
    CREATE TABLE IF NOT EXISTS results (
        username TEXT,
        case_id INTEGER,
        truth TEXT,
        user_guess TEXT,
        correct INTEGER,
        timestamp TEXT
    )
""")
conn.commit()
# If no users exist, create default demo users (with hashed passwords)
res = c.execute("SELECT COUNT(*) FROM users").fetchone()
if res and res[0] == 0:
    demo_users = {"radiologist1": "password1", "radiologist2": "password2"}
    for user, pw in demo_users.items():
        pw_hash = hashlib.sha256(pw.encode()).hexdigest()
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)", (user, pw_hash))
    conn.commit()
conn.close()

# Helper functions
def check_credentials(username: str, password: str) -> bool:
    """Verify username/password against the database (passwords stored as SHA-256 hashes)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?;", (username,))
        row = cur.fetchone()
        conn.close()
        if row:
            stored_pw_hash = row[0]
            input_pw_hash = hashlib.sha256(password.encode()).hexdigest()
            return input_pw_hash == stored_pw_hash
    except Exception as e:
        print("DB error on login:", e)
    return False

def load_user_progress(username: str):
    """Load completed cases and their outcomes for the given user from the database."""
    completed_cases = []
    progress = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT case_id, truth, user_guess, correct FROM results WHERE username=?;", (username,))
        rows = cur.fetchall()
        conn.close()
        for case_id, truth, guess, correct in rows:
            completed_cases.append(case_id)
            progress[case_id] = {"truth": truth, "guess": guess, "correct": correct}
    except Exception as e:
        print("DB error on load progress:", e)
    completed_cases = sorted(set(completed_cases))
    return completed_cases, progress

def save_result(username: str, case_id: int, truth: str, guess: str, correct: int):
    """Save a single evaluation result to the SQLite database and the user's CSV log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Save to SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO results (username, case_id, truth, user_guess, correct, timestamp)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (username, case_id, truth, guess, correct, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB error on save result:", e)
    # Append to CSV log
    log_file = os.path.join(LOGS_DIR, f"{username}_results.csv")
    file_exists = os.path.isfile(log_file)
    try:
        with open(log_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                writer.writerow(["username", "case_id", "truth", "user_guess", "correct", "timestamp"])
            writer.writerow([username, case_id, truth, guess, correct, timestamp])
    except Exception as e:
        print("Error writing to CSV log:", e)

# Determine list of case IDs available (by folder or file naming)
CASE_IDS = []
CASE_DIR_MAP = {}  # mapping case_id to actual folder name if applicable
if os.path.isdir("cases"):
    subdirs = [d for d in os.listdir("cases") if os.path.isdir(os.path.join("cases", d))]
    for d in subdirs:
        if d.isdigit():
            cid = int(d)
            CASE_IDS.append(cid); CASE_DIR_MAP[cid] = d
        elif d.lower().startswith("case"):
            num_part = ''.join(filter(str.isdigit, d))
            if num_part:
                cid = int(num_part)
                CASE_IDS.append(cid); CASE_DIR_MAP[cid] = d
    CASE_IDS = sorted(set(CASE_IDS))
    if not CASE_IDS:
        # If no case subfolders, try to infer from filenames in "cases" directory
        patterns = ["*AI*.png", "*AI*.jpg", "*GT*.png", "*GT*.jpg", "*Radiologist*.png", "*Radiologist*.jpg"]
        image_files = []
        for pat in patterns:
            image_files += glob.glob(os.path.join("cases", pat))
        for f in image_files:
            name = os.path.basename(f)
            num_str = ''.join(filter(str.isdigit, name))
            if num_str:
                CASE_IDS.append(int(num_str))
        CASE_IDS = sorted(set(CASE_IDS))
if not CASE_IDS:
    CASE_IDS = list(range(1, 11))  # default to 1-10 if data not found (for demo)

# Initialize session state on first run
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.completed_cases = []
    st.session_state.progress = {}
    st.session_state.current_case = None

# Sidebar: Login or Logout
if st.session_state.logged_in:
    st.sidebar.write(f"**Logged in as:** {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()
else:
    st.sidebar.title("User Login")
    username_input = st.sidebar.text_input("Username")
    password_input = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username_input and password_input and check_credentials(username_input, password_input):
            # Successful login
            st.session_state.logged_in = True
            st.session_state.username = username_input
            # Load user's past progress
            completed, progress = load_user_progress(username_input)
            st.session_state.completed_cases = completed
            st.session_state.progress = progress
            # Set starting case (first not completed)
            next_case = None
            for cid in CASE_IDS:
                if cid not in completed:
                    next_case = cid
                    break
            st.session_state.current_case = next_case
            st.rerun()
        else:
            st.sidebar.error("Invalid username or password")

# Main: only show Turing Test interface if logged in
if st.session_state.logged_in:
    st.title("Turing Test")
    if st.session_state.current_case is None:
        st.success("You have completed all cases. Thank you for your participation!")
    else:
        case_id = st.session_state.current_case
        total_cases = len(CASE_IDS)
        st.header(f"Case {case_id}")
        st.write(f"Progress: Case {CASE_IDS.index(case_id) + 1} of {total_cases}")
        # Randomly assign this case to show AI or Radiologist result (store in session for consistency)
        assign_key = f"assign_{case_id}"
        if assign_key not in st.session_state:
            import random
            st.session_state[assign_key] = random.choice(["AI", "Radiologist"])
        assignment = st.session_state[assign_key]  # "AI" or "Radiologist"
        # Load images for this case and assignment from the data folder
        images = []
        if os.path.isdir("cases"):
            folder_name = CASE_DIR_MAP.get(case_id, str(case_id))
            case_path = os.path.join("cases", folder_name)
            if os.path.isdir(case_path):
                if assignment == "Radiologist":
                    rad_dir = os.path.join(case_path, "Radiologist")
                    gt_dir = os.path.join(case_path, "GT")
                    if os.path.isdir(rad_dir):
                        images = sorted(glob.glob(os.path.join(rad_dir, "*.png")) + glob.glob(os.path.join(rad_dir, "*.jpg")))
                    elif os.path.isdir(gt_dir):
                        images = sorted(glob.glob(os.path.join(gt_dir, "*.png")) + glob.glob(os.path.join(gt_dir, "*.jpg")))
                    else:
                        # No subfolder; find files in case folder
                        images = sorted(glob.glob(os.path.join(case_path, "*Radiologist*.png")) +
                                        glob.glob(os.path.join(case_path, "*Radiologist*.jpg")) +
                                        glob.glob(os.path.join(case_path, "*GT*.png")) +
                                        glob.glob(os.path.join(case_path, "*GT*.jpg")))
                else:  # assignment == "AI"
                    ai_dir = os.path.join(case_path, "AI")
                    if os.path.isdir(ai_dir):
                        images = sorted(glob.glob(os.path.join(ai_dir, "*.png")) + glob.glob(os.path.join(ai_dir, "*.jpg")))
                    else:
                        images = sorted(glob.glob(os.path.join(case_path, "*AI*.png")) +
                                        glob.glob(os.path.join(case_path, "*AI*.jpg")))
            else:
                # No case-specific folder; look in top-level "cases" directory
                if assignment == "Radiologist":
                    images = sorted(glob.glob(os.path.join("cases", f"*{case_id}_Radiologist_*.png")) +
                                    glob.glob(os.path.join("cases", f"*{case_id}_Radiologist_*.jpg")) +
                                    glob.glob(os.path.join("cases", f"*{case_id}_GT_*.png")) +
                                    glob.glob(os.path.join("cases", f"*{case_id}_GT_*.jpg")))
                else:
                    images = sorted(glob.glob(os.path.join("cases", f"*{case_id}_AI_*.png")) +
                                    glob.glob(os.path.join("cases", f"*{case_id}_AI_*.jpg")))
        if not images:
            st.warning("Images for this case not found. Please ensure the data is available.")
        # Display image(s) with a slider if multiple
        if len(images) > 1:
            img_index = st.slider("Image", 1, len(images), 1)
            st.image(images[img_index - 1], use_column_width=True)
        elif len(images) == 1:
            st.image(images[0], use_column_width=True)
        # Choice input for Turing test (AI vs Radiologist)
        options = ["Please select an option", "AI", "Radiologist"]
        guess_key = f"guess_case_{case_id}"
        if guess_key not in st.session_state:
            st.session_state[guess_key] = options[0]
        st.radio("I think this annotation was generated by:", options, 
                 index=options.index(st.session_state[guess_key]) if st.session_state[guess_key] in options else 0, 
                 key=guess_key)
        # Enable submit only if a valid choice is made
        can_submit = st.session_state[guess_key] != options[0]
        if st.button("Submit", disabled=not can_submit):
            if not can_submit:
                st.warning("Please select an option before submitting.")
            else:
                user_guess = st.session_state[guess_key]  # "AI" or "Radiologist"
                truth = assignment  # actual identity of shown annotation
                correct = 1 if user_guess == truth else 0
                save_result(st.session_state.username, case_id, truth, user_guess, correct)
                # Update session progress
                st.session_state.completed_cases.append(case_id)
                st.session_state.progress[case_id] = {"truth": truth, "guess": user_guess, "correct": correct}
                # Determine next case
                next_case = None
                for cid in CASE_IDS:
                    if cid not in st.session_state.completed_cases:
                        next_case = cid
                        break
                st.session_state.current_case = next_case
                # Reset selection for this case to default and move on
                st.session_state[guess_key] = options[0]
                st.rerun()

import streamlit as st
import os
import json
import random
import pandas as pd
import glob

# --------------------------------------------------
# Sidebar: View Saved Logs Toggle
# --------------------------------------------------
# if "show_logs" not in st.session_state:
#     st.session_state.show_logs = False

# with st.sidebar:
#     if st.button("📊 View Saved Logs"):
#         st.session_state.show_logs = not st.session_state.show_logs
#     if st.session_state.show_logs:
#         st.subheader("Progress Logs (CSV)")
#         for filepath in sorted(glob.glob("logs/*_progress.csv")):
#             st.markdown(f"**{os.path.basename(filepath)}**")
#             try:
#                 df = pd.read_csv(filepath)
#                 st.dataframe(df)
#             except Exception as e:
#                 st.warning(f"Failed to read {filepath}: {e}")
#         st.subheader("Annotations (JSON)")
#         for filepath in sorted(glob.glob("evaluations/*_annotations.json")):
#             st.markdown(f"**{os.path.basename(filepath)}**")
#             try:
#                 with open(filepath, 'r', encoding='utf-8') as f:
#                     data = json.load(f)
#                 st.json(data)
#             except Exception as e:
#                 st.warning(f"Failed to read {filepath}: {e}")

# --------------------------------------------------
# Utility: Save Progress to JSON and CSV
# --------------------------------------------------
def save_progress(category: str, progress: dict):
    os.makedirs('logs', exist_ok=True)
    # JSON
    json_path = os.path.join('logs', f"{category}_progress.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)
    # CSV (overwrite latest state)
    csv_path = os.path.join('logs', f"{category}_progress.csv")
    df = pd.DataFrame([progress])
    df.to_csv(csv_path, index=False)

# --------------------------------------------------
# Utility: Save Annotations to JSON
# --------------------------------------------------
def save_annotations(case_id: str, annotations: list):
    os.makedirs('evaluations', exist_ok=True)
    save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, indent=2)

# --------------------------------------------------
# Initialize Session State for Each Workflow
# --------------------------------------------------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# Turing Test state keys
init_state("last_case_turing", 0)
init_state("current_slice_turing", 0)
init_state("assignments_turing", {})
init_state("initial_evaluation_turing", None)
init_state("final_evaluation_turing", None)
init_state("turing_test_submitted_turing", False)

# Standard Evaluation state keys
init_state("last_case_standard", 0)
init_state("current_slice_standard", 0)
init_state("assignments_standard", {})
init_state("corrections_standard", [])

# AI Edit state keys
init_state("last_case_ai", 0)
init_state("current_slice_ai", 0)
init_state("corrections_ai", [])
init_state("assembled_report_ai", "")

# --------------------------------------------------
# Query Parameter Setup
# --------------------------------------------------
query_params = st.experimental_get_query_params()
if "page" in query_params:
    st.session_state.page = query_params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

# --------------------------------------------------
# Paths & Cases
# --------------------------------------------------
BASE_IMAGE_DIR = "2D_Image"
if not os.path.exists(BASE_IMAGE_DIR):
    st.error(f"Directory not found: {BASE_IMAGE_DIR}")
    cases = []
else:
    cases = sorted([
        d for d in os.listdir(BASE_IMAGE_DIR)
        if os.path.isdir(os.path.join(BASE_IMAGE_DIR, d))
    ])
total_cases = len(cases)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def load_text_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def display_slice_carousel(category, case_id):
    slice_key = f"current_slice_{category}"
    folder = os.path.join(BASE_IMAGE_DIR, case_id)
    images = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]) if os.path.exists(folder) else []
    total = len(images)
    if total == 0:
        st.info("No slices available.")
        return
    # Clamp index
    idx = st.session_state[slice_key]
    idx = max(0, min(idx, total-1))
    st.session_state[slice_key] = idx

    c1, c2, c3 = st.columns([1, 8, 1])
    with c1:
        if st.button("⟨ Prev", key=f"prev_{category}_{case_id}") and idx > 0:
            st.session_state[slice_key] -= 1
            st.rerun()
    with c2:
        st.image(images[idx], width=600)
        st.caption(f"Slice {idx+1} of {total}")
    with c3:
        if st.button("Next ⟩", key=f"next_{category}_{case_id}") and idx < total-1:
            st.session_state[slice_key] += 1
            st.rerun()

def reset_all_state():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_set_query_params(page="index")
    st.rerun()

# --------------------------------------------------
# Page: Turing Test
# --------------------------------------------------
def turing_test():
    idx = st.session_state.last_case_turing
    if idx >= total_cases or not cases:
        st.markdown("### Turing Test complete.")
        if st.button("Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[idx]
    st.header(f"Turing Test: Case {idx+1}/{total_cases} — {case_id}")

    # Save Progress
    if st.button("Save & Back", key=f"save_turing_{case_id}"):
        progress = {
            "last_case": idx,
            "assignments": st.session_state.assignments_turing,
            "initial_eval": st.session_state.initial_evaluation_turing,
            "final_eval": st.session_state.final_evaluation_turing,
            "viewed_images": st.session_state.turing_test_submitted_turing
        }
        save_progress("turing_test", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load reports
    gt = load_text_file(os.path.join(BASE_IMAGE_DIR, case_id, "text.txt"))
    ai = load_text_file(os.path.join(BASE_IMAGE_DIR, case_id, "pred.txt"))

    # Assignment
    assignments = st.session_state.assignments_turing
    if case_id not in assignments:
        assignments[case_id] = random.choice([True, False])
        st.session_state.assignments_turing = assignments
    assign_A = assignments[case_id]

    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai
    st.subheader("Report A")
    st.text_area("A", reportA, height=250, key=f"rpA_t_{case_id}")
    st.subheader("Report B")
    st.text_area("B", reportB, height=250, key=f"rpB_t_{case_id}")

    # Initial evaluation
    if st.session_state.initial_evaluation_turing is None:
        choice = st.radio("Which is ground truth?", ["Report A", "Report B", "Not sure"], key=f"ch_t_{case_id}", index=2)
        if st.button("Submit Initial", key=f"subi_t_{case_id}"):
            st.session_state.initial_evaluation_turing = choice
            st.session_state.turing_test_submitted_turing = True
            st.success(f"Recorded: {choice}")
            st.rerun()

    # After viewing images
    if st.session_state.turing_test_submitted_turing:
        st.markdown("#### Images")
        display_slice_carousel("turing", case_id)
        st.markdown(f"**Initial:** {st.session_state.initial_evaluation_turing}")
        upd = st.radio("After images:", ["Keep", "Update"], key=f"up_t_{case_id}")
        final = st.session_state.initial_evaluation_turing
        if upd == "Update":
            final = st.radio("New choice:", ["Report A", "Report B", "Not sure"], key=f"new_t_{case_id}", index=2)
        st.session_state.final_evaluation_turing = final
        if st.button("Finalize & Next", key=f"final_t_{case_id}"):
            st.session_state.last_case_turing += 1
            st.session_state.current_slice_turing = 0
            st.session_state.initial_evaluation_turing = None
            st.session_state.final_evaluation_turing = None
            st.session_state.turing_test_submitted_turing = False
            st.rerun()

# --------------------------------------------------
# Page: Standard Evaluation
# --------------------------------------------------
def evaluate_case():
    idx = st.session_state.last_case_standard
    if idx >= total_cases or not cases:
        st.markdown("### Standard Evaluation complete.")
        if st.button("Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[idx]
    st.header(f"Standard Eval: Case {idx+1}/{total_cases} — {case_id}")

    # Save Progress
    if st.button("Save & Back", key=f"save_std_{case_id}"):
        progress = {
            "last_case": idx,
            "assignments": st.session_state.assignments_standard,
            "corrections": st.session_state.corrections_standard
        }
        save_progress("standard_evaluation", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load reports
    gt = load_text_file(os.path.join(BASE_IMAGE_DIR, case_id, "text.txt"))
    ai = load_text_file(os.path.join(BASE_IMAGE_DIR, case_id, "pred.txt"))

    # Assignment
    assignments = st.session_state.assignments_standard
    if case_id not in assignments:
        assignments[case_id] = random.choice([True, False])
        st.session_state.assignments_standard = assignments
    assign_A = assignments[case_id]

    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai
    st.subheader("Report A")
    st.text_area("A", reportA, height=200, key=f"rpA_s_{case_id}")
    st.subheader("Report B")
    st.text_area("B", reportB, height=200, key=f"rpB_s_{case_id}")

    # Images
    st.markdown("#### Images")
    display_slice_carousel("standard", case_id)

    # Corrections
    st.markdown("#### Corrections")
    organs = ["LIVER","PANCREAS","KIDNEY","OTHER"]
    new = st.selectbox("Organ", [""]+organs, key=f"org_s_{case_id}")
    reason = st.text_input("Reason", key=f"rsn_s_{case_id}")
    details = st.text_area("Details", key=f"dtl_s_{case_id}")
    if st.button("Add Correction", key=f"add_s_{case_id}") and new:
        st.session_state.corrections_standard.append({
            "case_id": case_id, "organ": new,
            "reason": reason, "details": details
        })
        st.success("Added")
        st.rerun()

    # Show table
    cors = [c for c in st.session_state.corrections_standard if c["case_id"]==case_id]
    if cors:
        df = pd.DataFrame(cors).drop(columns=["case_id"])
        st.table(df)

    choice = st.radio("Which best?", ["A","B","Corrected","Equal"], key=f"ch_s_{case_id}")
    if st.button("Submit & Next", key=f"sub_s_{case_id}"):
        if cors:
            save_annotations(case_id, cors)
        st.session_state.corrections_standard = [
            c for c in st.session_state.corrections_standard if c["case_id"]!=case_id
        ]
        st.session_state.last_case_standard += 1
        st.session_state.current_slice_standard = 0
        st.rerun()

# --------------------------------------------------
# Page: AI Report Editing
# --------------------------------------------------
def ai_edit():
    idx = st.session_state.last_case_ai
    if idx >= total_cases or not cases:
        st.markdown("### AI Editing complete.")
        if st.button("Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[idx]
    st.header(f"AI Edit: Case {idx+1}/{total_cases} — {case_id}")

    if st.button("Save & Back", key=f"save_ai_{case_id}"):
        progress = {
            "last_case": idx,
            "assembled_report": st.session_state.assembled_report_ai,
            "corrections": st.session_state.corrections_ai
        }
        save_progress("ai_edit", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Show original AI report
    ai_txt = load_text_file(os.path.join(BASE_IMAGE_DIR, case_id, "pred.txt"))
    st.subheader("Original AI Report")
    st.text_area("orig_ai", ai_txt, height=200, disabled=True)

    # Images
    st.markdown("#### Images")
    display_slice_carousel("ai", case_id)

    mode = st.radio("Mode", ["Free","Organ-by-Organ"], key=f"md_ai_{case_id}")
    if mode=="Free":
        # Free edit
        content = st.session_state.assembled_report_ai or ai_txt
        new_txt = st.text_area("Edit", content, height=300, key=f"free_ai_{case_id}")
        st.session_state.assembled_report_ai = new_txt

    else:
        # Organ-by-organ
        organs = ["LIVER","PANCREAS","KIDNEY","OTHER"]
        new = st.selectbox("Organ", [""]+organs, key=f"org_ai_{case_id}")
        reason = st.text_input("Reason", key=f"rsn_ai_{case_id}")
        details = st.text_area("Details", key=f"dtl_ai_{case_id}")
        if st.button("Add Corr", key=f"add_ai_{case_id}") and new:
            st.session_state.corrections_ai.append({
                "case_id": case_id, "organ": new,
                "reason": reason, "details": details
            })
            st.success("Added")
            st.rerun()
        cors = [c for c in st.session_state.corrections_ai if c["case_id"]==case_id]
        if cors:
            df = pd.DataFrame(cors).drop(columns=["case_id"])
            st.table(df)
            if st.button("Assemble", key=f"asm_ai_{case_id}"):
                text = "\n".join(f"- {c['organ']}: {c['reason']} — {c['details']}" for c in cors)
                st.session_state.assembled_report_ai = text
                st.success("Assembled")
                st.rerun()

    if st.button("Submit & Next", key=f"sub_ai_{case_id}"):
        # (Optionally) save final report here
        st.session_state.corrections_ai = [
            c for c in st.session_state.corrections_ai if c["case_id"]!=case_id
        ]
        st.session_state.assembled_report_ai = ""
        st.session_state.last_case_ai += 1
        st.session_state.current_slice_ai = 0
        st.rerun()

# --------------------------------------------------
# Page: View All Results
# --------------------------------------------------
def view_all_results():
    st.header("All Saved Progress & Annotations")
    if st.button("Home"):
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()
    st.subheader("Progress CSVs")
    for f in sorted(glob.glob("logs/*_progress.csv")):
        st.markdown(f"**{os.path.basename(f)}**")
        try:
            st.dataframe(pd.read_csv(f))
        except:
            st.warning(f"Can't read {f}")
    st.subheader("Annotation JSONs")
    for f in sorted(glob.glob("evaluations/*_annotations.json")):
        st.markdown(f"**{os.path.basename(f)}**")
        try:
            with open(f) as fp: st.json(json.load(fp))
        except:
            st.warning(f"Can't read {f}")

# --------------------------------------------------
# Index / Navigation
# --------------------------------------------------
def index():
    st.title("Survey App")
    if total_cases == 0:
        st.error("No cases found.")
        return
   st.markdown("### Your Progress So Far")
    st.markdown(
        f"- **Turing Test**: Case {st.session_state.last_case_turing + 1} of {total_cases}"
    )
    st.markdown(
        f"- **Standard Evaluation**: Case {st.session_state.last_case_standard + 1} of {total_cases}"
    )
    st.markdown(
        f"- **AI Report Editing**: Case {st.session_state.last_case_ai + 1} of {total_cases}"
    )
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Turing Test"):
        st.experimental_set_query_params(page="turing_test")
        st.session_state.page = "turing_test"
        st.rerun()
    if c2.button("Standard Eval"):
        st.experimental_set_query_params(page="evaluate_case")
        st.session_state.page = "evaluate_case"
        st.rerun()
    if c3.button("AI Edit"):
        st.experimental_set_query_params(page="ai_edit")
        st.session_state.page = "ai_edit"
        st.rerun()
    if c4.button("View Results"):
        st.experimental_set_query_params(page="view_results")
        st.session_state.page = "view_results"
        st.rerun()

# --------------------------------------------------
# Main Routing
# --------------------------------------------------
page = st.session_state.page
if page == "turing_test":
    turing_test()
elif page == "evaluate_case":
    evaluate_case()
elif page == "ai_edit":
    ai_edit()
elif page == "view_results":
    view_all_results()
else:
    index()

import streamlit as st
import os
import json
import random
import pandas as pd
import glob

# --------------------------------------------------
# Sidebar: View Saved Logs
# --------------------------------------------------
with st.sidebar:
    if st.button("View Saved Logs"):
        st.subheader("Progress Logs (CSV)")
        for filepath in glob.glob("logs/*_progress.csv"):
            st.markdown(f"**{os.path.basename(filepath)}**")
            try:
                df = pd.read_csv(filepath)
                st.dataframe(df)
            except Exception as e:
                st.write(f"Failed to read {filepath}: {e}")
        st.subheader("Annotations (JSON)")
        for filepath in glob.glob("evaluations/*_annotations.json"):
            name = os.path.basename(filepath)
            st.markdown(f"**{name}**")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.json(data)
            except Exception as e:
                st.write(f"Failed to read {filepath}: {e}")

# --------------------------------------------------
# Utility: Save Progress to JSON and CSV
# --------------------------------------------------
def save_progress(category: str, progress: dict):
    os.makedirs('logs', exist_ok=True)
    # JSON
    json_path = os.path.join('logs', f"{category}_progress.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)
    # CSV
    csv_path = os.path.join('logs', f"{category}_progress.csv")
    df = pd.DataFrame([progress])
    mode = 'a' if os.path.exists(csv_path) else 'w'
    df.to_csv(csv_path, mode=mode, index=False, header=(mode=='w'))

# --------------------------------------------------
# Utility: Save Annotations to JSON
# --------------------------------------------------
def save_annotations(case_id: str, annotations: list):
    os.makedirs('evaluations', exist_ok=True)
    save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(annotations, f, indent=2)

# --------------------------------------------------
# Query Parameters & Session‐State Initialization
# --------------------------------------------------
query_params = st.experimental_get_query_params()
if "page" in query_params:
    st.session_state.page = query_params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# Turing Test state
init_state("last_case_turing", 0)
init_state("assignments_turing", {})
init_state("current_slice_turing", 0)
init_state("initial_evaluation_turing", None)
init_state("final_evaluation_turing", None)
init_state("turing_test_submitted", False)

# Standard evaluation state
init_state("last_case_standard", 0)
init_state("assignments_standard", {})
init_state("current_slice_standard", 0)
init_state("corrections_standard", [])

# AI edit state
init_state("last_case_ai", 0)
init_state("current_slice_ai", 0)
init_state("ai_corrections", [])
init_state("assembled_report_ai", "")

# --------------------------------------------------
# Define Cases
# --------------------------------------------------
BASE_IMAGE_DIR = r"2D_Image"
cases = sorted([f for f in os.listdir(BASE_IMAGE_DIR)
                if os.path.isdir(os.path.join(BASE_IMAGE_DIR, f))])
total_cases = len(cases)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def load_text_file(file_path):
    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def display_slice_carousel(case_id, slice_key):
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    images = sorted([os.path.join(subfolder, f)
                     for f in os.listdir(subfolder)
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    total = len(images)
    if total == 0:
        st.info("No slices found for this case.")
        return
    col1, col2, col3 = st.columns([1,8,1])
    with col1:
        if st.button("⟨ Prev", key=f"prev_{slice_key}_{case_id}") and st.session_state[slice_key] > 0:
            st.session_state[slice_key] -= 1
            st.rerun()
    with col2:
        idx = st.session_state[slice_key]
        st.image(images[idx], width=600)
        st.caption(f"Slice {idx+1} of {total}")
    with col3:
        if st.button("Next ⟩", key=f"next_{slice_key}_{case_id}") and st.session_state[slice_key] < total-1:
            st.session_state[slice_key] += 1
            st.rerun()

def reset_evaluation():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.experimental_set_query_params(page="index")
    st.rerun()

# --------------------------------------------------
# 1. Turing Test Page
# --------------------------------------------------
def turing_test():
    idx = st.session_state.last_case_turing
    if idx >= total_cases:
        st.markdown("### Turing Test complete. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[idx]
    st.markdown(f"### Turing Test for Case: **{case_id}** ({idx+1}/{total_cases})")

    # Save Progress button
    if st.button("Save Progress & Go Back", key=f"save_turing_{case_id}"):
        progress = {
            "last_case": idx,
            "assignments": st.session_state.assignments_turing,
            "initial_evaluation": st.session_state.initial_evaluation_turing,
            "turing_test_submitted": st.session_state.turing_test_submitted
        }
        save_progress("turing_test", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load & display reports
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    gt = load_text_file(os.path.join(subfolder, "text.txt"))
    ai = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Assignment order
    assignments = st.session_state.assignments_turing
    if str(idx) not in assignments:
        assignments[str(idx)] = random.choice([True, False])
        st.session_state.assignments_turing = assignments
    assign_A = assignments[str(idx)]
    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai

    st.markdown("#### Report A")
    st.text_area("Report A", reportA, height=300, key=f"reportA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB, height=300, key=f"reportB_{case_id}")

    # Initial evaluation
    if st.session_state.initial_evaluation_turing is None:
        choice = st.radio("Which report is ground truth?",
                          ("Report A", "Report B", "Not sure"),
                          key=f"choice_{case_id}")
        if st.button("Submit Evaluation (Initial)", key=f"submit_initial_{case_id}"):
            st.session_state.initial_evaluation_turing = choice
            st.session_state.turing_test_submitted = True
            st.success(f"Initial evaluation recorded: {choice}")
            st.rerun()
    else:
        st.markdown("### Evaluation (After Viewing Images)")
        display_slice_carousel(case_id, "current_slice_turing")
        st.markdown(f"**Your initial evaluation was:** {st.session_state.initial_evaluation_turing}")

        upd = st.radio("Update Evaluation",
                       ("Keep initial", "Update"),
                       key=f"upd_{case_id}")
        if upd == "Keep initial":
            final = st.session_state.initial_evaluation_turing
        else:
            final = st.radio("Select new evaluation",
                             ("Report A", "Report B", "Not sure"),
                             key=f"new_{case_id}")
        if st.button("Record Final Evaluation", key=f"rec_final_{case_id}"):
            st.session_state.final_evaluation_turing = final
            st.success(f"Final evaluation recorded: {final}")
        if st.button("Continue to Next Case", key=f"cont_{case_id}"):
            st.session_state.last_case_turing = idx + 1
            st.session_state.current_slice_turing = 0
            st.session_state.initial_evaluation_turing = None
            st.session_state.final_evaluation_turing = None
            st.session_state.turing_test_submitted = False
            st.rerun()

# --------------------------------------------------
# 2. Standard Evaluation Page
# --------------------------------------------------
def evaluate_case():
    idx = st.session_state.last_case_standard
    if idx >= total_cases:
        st.markdown("### Evaluation complete. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
        return

    case_id = cases[idx]
    st.markdown(f"### Evaluating Case: **{case_id}** ({idx+1}/{total_cases})")

    # Save Progress button
    if st.button("Save Progress & Go Back", key=f"save_eval_{case_id}"):
        case_corrs = [c for c in st.session_state.corrections_standard if c["case_id"] == case_id]
        progress = {"last_case": idx, "corrections": case_corrs}
        save_progress("standard_evaluation", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load & display
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    gt = load_text_file(os.path.join(subfolder, "text.txt"))
    ai = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Assignment
    assignments = st.session_state.assignments_standard
    if str(idx) not in assignments:
        assignments[str(idx)] = random.choice([True, False])
        st.session_state.assignments_standard = assignments
    assign_A = assignments[str(idx)]
    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai

    st.markdown("#### Report A")
    st.text_area("Report A", reportA, height=200, key=f"evalA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB, height=200, key=f"evalB_{case_id}")

    # Images
    st.markdown("#### Slice Images")
    display_slice_carousel(case_id, "current_slice_standard")

    # Corrections
    st.markdown("#### Corrections / Annotations")
    detected_organs = ["LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
                       "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"]
    selected = [o for o in detected_organs if st.checkbox(o, key=f"org_{case_id}_{o}")]
    if selected:
        organ = st.selectbox("Organ to correct", options=selected, key=f"sel_org_{case_id}")
        reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
        reason = st.selectbox("Reason", options=reasons, key=f"reason_{case_id}")
        final_reason = (st.text_input("Specify other reason", key=f"oth_reason_{case_id}")
                        if reason == "Other" else reason)
        detail = st.text_area("Correction details", key=f"corr_txt_{case_id}")
        if st.button("Add Correction", key=f"add_corr_{case_id}"):
            st.session_state.corrections_standard.append({
                "case_id": case_id,
                "organ": organ,
                "reason": final_reason,
                "details": detail
            })
            st.success("Correction added!")
            st.rerun()

    # Show existing
    case_corrs = [c for c in st.session_state.corrections_standard if c["case_id"] == case_id]
    if case_corrs:
        corr_df = pd.DataFrame(case_corrs).drop(columns=["case_id"])
        st.table(corr_df)

    # Final choice & submit
    evaluation_choice = st.radio(
        "Select which report is best:",
        ("Report A is better", "Report B is better", "Corrected Report is better", "Equivalent")
        if st.session_state.assembled_report_ai else
        ("Report A is better", "Report B is better", "Equivalent"),
        key=f"eval_choice_{case_id}"
    )
    if st.button("Submit All Corrections", key=f"sub_corr_{case_id}"):
        try:
            save_annotations(case_id, case_corrs)
            st.success(f"Annotations saved. Evaluation: {evaluation_choice}")
            # clear corrections for this case
            st.session_state.corrections_standard = [
                c for c in st.session_state.corrections_standard
                if c["case_id"] != case_id
            ]
            st.session_state.last_case_standard = idx + 1
            st.session_state.current_slice_standard = 0
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save annotations: {e}")

# --------------------------------------------------
# 3. AI Edit Page
# --------------------------------------------------
def ai_edit():
    idx = st.session_state.last_case_ai
    if idx >= total_cases:
        st.markdown("### All cases have been edited. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[idx]
    st.markdown(f"### AI Report Editing for Case: **{case_id}** ({idx+1}/{total_cases})")

    # Save Progress button
    if st.button("Save Progress & Go Back", key=f"save_ai_{case_id}"):
        progress = {
            "last_case": idx,
            "assembled_report": st.session_state.assembled_report_ai
        }
        save_progress("ai_edit", progress)
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load & display
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))
    st.markdown("#### AI Report")
    st.text_area("AI Report", ai_report, height=200, key=f"ai_overview_{case_id}")

    # Choose mode
    edit_mode = st.radio("Choose Editing Mode:",
                         ("Free Editing", "Organ-by-Organ Editing"),
                         key=f"mode_{case_id}")
    if edit_mode == "Free Editing":
        final_report = st.text_area("Edit the AI-generated report",
                                   ai_report, height=300,
                                   key=f"free_edit_{case_id}")
        st.session_state.assembled_report_ai = final_report
    else:
        detected_organs = ["LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
                           "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"]
        selected = [o for o in detected_organs
                    if st.checkbox(o, key=f"org_ai_{case_id}_{o}")]
        if selected:
            organ = st.selectbox("Select an organ to correct",
                                 options=selected, key=f"select_ai_{case_id}")
            reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
            reason = st.selectbox("Reason", options=reasons, key=f"reason_ai_{case_id}")
            final_reason = (st.text_input("If Other, specify", key=f"oth_ai_{case_id}")
                            if reason == "Other" else reason)
            detail = st.text_area("Correction details", key=f"detail_ai_{case_id}")
            if st.button("Add Correction", key=f"add_ai_corr_{case_id}"):
                st.session_state.ai_corrections.append({
                    "case_id": case_id,
                    "organ": organ,
                    "reason": final_reason,
                    "details": detail
                })
                st.success("Correction added!")
                st.rerun()

        # show per‐case corrections
        case_ai_corrs = [c for c in st.session_state.ai_corrections
                         if c["case_id"] == case_id]
        if case_ai_corrs:
            df = pd.DataFrame(case_ai_corrs).drop(columns=["case_id"])
            st.table(df)
            if st.button("Assemble Corrected Report", key=f"assemble_{case_id}"):
                assembled = "Organ-by-Organ Corrected Report:\n\n"
                for c in case_ai_corrs:
                    assembled += f"{c['organ']}: {c['reason']} - {c['details']}\n\n"
                st.session_state.assembled_report_ai = assembled
                st.success("Corrected report assembled!")
                st.rerun()

    if st.button("Submit Edited Report", key=f"sub_edit_{case_id}"):
        st.success("Edited report submitted.")
        st.session_state.last_case_ai = idx + 1
        st.session_state.current_slice_ai = 0
        st.rerun()

# --------------------------------------------------
# 4. Landing Page & Navigation
# --------------------------------------------------
def index():
    last = max(st.session_state.last_case_turing,
               st.session_state.last_case_standard,
               st.session_state.last_case_ai)
    if last >= total_cases:
        st.markdown("### All workflows complete. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
    else:
        st.markdown("### Welcome to the Survey")
        st.markdown(f"We have **{total_cases}** case(s) to work on.")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Start Turing Test"):
                st.experimental_set_query_params(page="turing_test")
                st.session_state.page = "turing_test"
                st.rerun()
        with c2:
            if st.button("Start AI Report Editing"):
                st.experimental_set_query_params(page="ai_edit")
                st.session_state.page = "ai_edit"
                st.rerun()
        with c3:
            if st.button("Start Standard Evaluation"):
                st.experimental_set_query_params(page="evaluate_case")
                st.session_state.page = "evaluate_case"
                st.rerun()

# --------------------------------------------------
# 5. Main Navigation
# --------------------------------------------------
if st.session_state.page == "index":
    index()
elif st.session_state.page == "turing_test":
    turing_test()
elif st.session_state.page == "evaluate_case":
    evaluate_case()
elif st.session_state.page == "ai_edit":
    ai_edit()
else:
    index()

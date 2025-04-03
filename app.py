import streamlit as st
import os, json, random, time
import pandas as pd

# --- Query Parameter Setup ---
query_params = st.experimental_get_query_params()
if "page" in query_params:
    st.session_state.page = query_params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

# --- Initialize Session State ---
if "last_case" not in st.session_state:
    st.session_state.last_case = 0
if "assignments" not in st.session_state:
    st.session_state.assignments = {}
if "current_slice" not in st.session_state:
    st.session_state.current_slice = 0
# Removed edit_timer from session_state as per feedback

# For Turing test image reveal flag per case:
# This flag is stored with key "show_images_{case_id}"

# --- Set up base directory paths ---
BASE_IMAGE_DIR = r'2D_Image'

# --- Load CSV and filter desired cases ---
try:
    labels_df = pd.read_csv(label_path)
except Exception as e:
    st.error(f"Failed to load dataset: {str(e)}")
    st.stop()

labels_df['XNATSessionID'] = labels_df['XNATSessionID'].astype(str)
desired_cases = ['C-78', 'C-134', 'C-154']
cases = [case for case in desired_cases if case in labels_df['XNATSessionID'].values]
total_cases = len(cases)
st.write("Evaluating cases:", cases)

def extract_findings(report_text):
    """
    Extracts and returns the findings section from a report.
    If "findings:" is present (case-insensitive), returns that section.
    """
    lower_text = report_text.lower()
    idx = lower_text.find("findings:")
    if idx != -1:
        return report_text[idx:]
    return report_text

def save_annotations(case_id, annotations):
    os.makedirs('evaluations', exist_ok=True)
    save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
    with open(save_path, 'w') as f:
        json.dump(annotations, f, indent=2)

# --- Modified image carousel with larger images and technical notes ---
def display_slice_carousel(case_id):
    slice_images = []
    tech_notes = {}  # Placeholder mapping: replace with actual technical notes
    for i in range(1, 33):
        filename = f"{case_id}_img_slice_{i}.png"
        full_path = os.path.join(BASE_IMAGE_DIR, filename)
        if os.path.exists(full_path):
            slice_images.append(full_path)
            tech_notes[i-1] = f"Technical note for slice {i}"
    slice_images.sort()
    total_slices = len(slice_images)
    if total_slices == 0:
        st.info("No slices found")
        return

    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        if st.button("⟨ Prev", key=f"prev_{case_id}"):
            if st.session_state.current_slice > 0:
                st.session_state.current_slice -= 1
                st.rerun()
    with col2:
        st.image(slice_images[st.session_state.current_slice], width=600)
        st.caption(f"Slice {st.session_state.current_slice + 1} of {total_slices}")
        st.markdown(f"*{tech_notes.get(st.session_state.current_slice, 'No note available')}*")
    with col3:
        if st.button("Next ⟩", key=f"next_{case_id}"):
            if st.session_state.current_slice < total_slices - 1:
                st.session_state.current_slice += 1
                st.rerun()

# --- Placeholder function to “neutralize” report language (to be further refined) ---
def neutralize_report(report):
    # In practice, use NLP techniques to balance language style.
    return report

# --- Turing Test Session ---
def turing_test():
    case_index = st.session_state.last_case
    if case_index >= total_cases:
        st.markdown("### Turing Test complete. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[case_index]
    st.session_state.last_case = case_index  # track progress

    row = labels_df[labels_df['XNATSessionID'] == case_id]
    if row.empty:
        st.error(f"Case {case_id} not found in CSV.")
        return

    ground_truth_report = row['Ground Truth'].values[0]
    ai_report = row['pred'].values[0]
    neutral_ai = neutralize_report(ai_report)
    neutral_gt = neutralize_report(ground_truth_report)

    assignments = st.session_state.get('assignments', {})
    if str(case_index) in assignments:
        assign_A = assignments[str(case_index)]
    else:
        assign_A = random.choice([True, False])
        assignments[str(case_index)] = assign_A
        st.session_state.assignments = assignments

    if assign_A:
        reportA_text = neutral_ai
        reportB_text = neutral_gt
    else:
        reportA_text = neutral_gt
        reportB_text = neutral_ai

    st.markdown(f"### Turing Test Evaluation for Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    st.markdown("#### Report A")
    st.text_area("Report A", reportA_text, height=300, key=f"reportA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB_text, height=300, key=f"reportB_{case_id}")

    # Check if images have been revealed for this case.
    image_key = f"show_images_{case_id}"
    if image_key not in st.session_state:
        st.session_state[image_key] = False

    # Provide a button to reveal images
    if not st.session_state[image_key]:
        if st.button("Reveal Slice Images", key=f"reveal_images_{case_id}"):
            st.session_state[image_key] = True
            st.rerun()
    else:
        st.markdown("#### Slice Images")
        display_slice_carousel(case_id)

    st.markdown("#### Evaluation")
    # If an assembled corrected report exists, add it as a third option.
    if "assembled_report" in st.session_state and st.session_state.assembled_report:
        choice = st.radio("Select which report is better:",
                          ("Report A is better", "Report B is better", "Corrected Report is better"),
                          key=f"choice_{case_id}")
    else:
        choice = st.radio("Select which report is better:",
                          ("Report A is better", "Report B is better", "Equivalent"),
                          key=f"choice_{case_id}")
    if st.button("Submit Turing Test Evaluation", key=f"submit_turing_{case_id}"):
        st.success(f"Submitted evaluation: {choice}")
        st.session_state.last_case = case_index + 1
        st.rerun()

# --- AI Report Editing Session ---
def ai_edit():
    case_index = st.session_state.last_case
    if case_index >= total_cases:
        st.markdown("### All cases have been edited. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return

    case_id = cases[case_index]
    row = labels_df[labels_df['XNATSessionID'] == case_id]
    if row.empty:
        st.error(f"Case {case_id} not found in CSV.")
        return

    ai_report = row['pred'].values[0]
    st.markdown(f"### AI Report Editing for Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    st.markdown("#### AI Report")
    
    # Select editing mode: free or organ-by-organ
    edit_mode = st.radio("Choose Editing Mode:", ("Free Editing", "Organ-by-Organ Editing"), key=f"edit_mode_{case_id}")
    
    if edit_mode == "Free Editing":
        edited_report = st.text_area("Edit the AI-generated report", ai_report, height=300, key=f"ai_edit_{case_id}")
        final_report = edited_report  # Free editing output
    else:
        st.markdown("### Organ-by-Organ Editing Navigation")
        st.markdown("**Step 1: Select Organs for Correction**")
        detected_organs = [
            "LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS", 
            "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"
        ]
        st.write("Please select the organs you wish to correct:")
        selected_organs = [organ for organ in detected_organs if st.checkbox(organ, key=f"organ_{organ}_{case_id}")]
        
        if selected_organs:
            st.markdown("**Step 2: Provide Correction Details for the Selected Organ**")
            organ_to_correct = st.selectbox("Select an organ to correct", options=selected_organs, key=f"organ_select_{case_id}")
            predefined_reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
            reason_choice = st.selectbox("Select the reason for the correction", options=predefined_reasons, key=f"reason_choice_{case_id}")
            final_reason = st.text_input("If Other, please specify", key=f"reason_text_{case_id}") if reason_choice == "Other" else reason_choice
            correction_text = st.text_area("Enter the correction details", key=f"correction_text_{case_id}")
            
            if st.button("Add Correction", key=f"add_correction_{case_id}"):
                new_correction = {
                    "organ": organ_to_correct,
                    "reason": final_reason,
                    "details": correction_text
                }
                if "corrections" not in st.session_state:
                    st.session_state["corrections"] = []
                st.session_state["corrections"].append(new_correction)
                st.success("Correction added!")
                st.rerun()
            
            st.markdown("**Step 3: Review Your Corrections**")
            if st.session_state.get("corrections"):
                corrections_df = pd.DataFrame(st.session_state["corrections"])
                st.table(corrections_df)
                if st.button("Assemble Corrected Report", key=f"assemble_report_{case_id}"):
                    # Concatenate corrections to form the corrected report.
                    assembled = "Organ-by-Organ Corrected Report:\n\n"
                    for corr in st.session_state["corrections"]:
                        assembled += f"{corr['organ']}: {corr['reason']} - {corr['details']}\n\n"
                    st.session_state["assembled_report"] = assembled
                    st.success("Corrected report assembled!")
                    st.rerun()
            else:
                st.info("No corrections added yet.")
        final_report = st.session_state.get("assembled_report", "")
    
    # Removed timer functionality as per feedback.
    if st.button("Submit Edited Report", key=f"submit_edit_{case_id}"):
        st.success("Edited report submitted.")
        # Store final_report as needed.
        st.session_state.last_case = case_index + 1
        st.rerun()

# --- Standard Evaluation Session ---
def evaluate_case():
    case_index = st.session_state.last_case
    if case_index >= total_cases:
        st.markdown("### Evaluation complete. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
        return

    case_id = cases[case_index]
    st.session_state.last_case = case_index

    row = labels_df[labels_df['XNATSessionID'] == case_id]
    if row.empty:
        st.error(f"Case {case_id} not found in CSV.")
        return

    ground_truth_report = row['Ground Truth'].values[0]
    ai_report = row['pred'].values[0]
    gt_finding = extract_findings(ground_truth_report)
    ai_finding = extract_findings(ai_report)

    assignments = st.session_state.get('assignments', {})
    if str(case_index) in assignments:
        assign_A = assignments[str(case_index)]
    else:
        assign_A = random.choice([True, False])
        assignments[str(case_index)] = assign_A
        st.session_state.assignments = assignments

    # Use the assembled corrected report if available (from organ-by-organ editing)
    corrected_report = st.session_state.get("assembled_report", None)
    
    if assign_A:
        reportA_text = ai_report
        reportB_text = ground_truth_report
    else:
        reportA_text = ground_truth_report
        reportB_text = ai_report

    st.markdown(f"### Evaluating Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    st.markdown("#### Report A")
    st.text_area("Report A", reportA_text, height=300, key=f"eval_reportA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB_text, height=300, key=f"eval_reportB_{case_id}")
    
    if corrected_report:
        st.markdown("#### Corrected Report (from Organ-by-Organ Editing)")
        st.text_area("Corrected Report", corrected_report, height=300, key=f"eval_corrected_{case_id}")
        eval_options = ("Report A is better", "Report B is better", "Corrected Report is better", "Equivalent")
    else:
        eval_options = ("Report A is better", "Report B is better", "Equivalent")
    
    st.markdown("#### Slice Images")
    display_slice_carousel(case_id)
    
    st.markdown("#### Corrections / Annotations")
    detected_organs = [
        "LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS", 
        "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"
    ]
    st.write("Select the organs you want to correct:")
    selected_organs = [organ for organ in detected_organs if st.checkbox(organ, key=f"eval_organ_{organ}_{case_id}")]
    
    if selected_organs:
        st.write("Enter correction details:")
        organ_to_correct = st.selectbox("Organ to correct", options=selected_organs, key="eval_organ_select")
        predefined_reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
        reason_choice = st.selectbox("Reason for disagreement", options=predefined_reasons, key="eval_reason_choice")
        final_reason = st.text_input("Specify other reason", key="eval_reason_text") if reason_choice == "Other" else reason_choice
        correction_text = st.text_area("Correction details", key="eval_correction_text")
        
        if st.button("Add Correction", key=f"eval_add_correction_{case_id}"):
            new_correction = {
                "organ": organ_to_correct,
                "reason": final_reason,
                "details": correction_text
            }
            if "corrections" not in st.session_state:
                st.session_state["corrections"] = []
            st.session_state["corrections"].append(new_correction)
            st.success("Correction added!")
            st.rerun()
    
    if st.session_state.get("corrections"):
        st.markdown("#### Current Corrections")
        corrections_df = pd.DataFrame(st.session_state["corrections"])
        st.table(corrections_df)
    
    if st.button("Submit All Corrections", key=f"submit_eval_{case_id}"):
        try:
            corrections = st.session_state["corrections"]
            save_annotations(case_id, corrections)
            st.success("Annotations saved.")
            st.session_state["corrections"] = []
            if "assembled_report" in st.session_state:
                st.session_state["assembled_report"] = ""
            st.session_state.last_case = case_index + 1
            st.session_state.current_slice = 0
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save annotations: {e}")

# --- Reset function ---
def reset_evaluation():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_set_query_params(page="index")
    st.rerun()

# --- Landing Page ---
def index():
    last_case = st.session_state.last_case
    if last_case >= total_cases:
        st.markdown("### All selected cases have been evaluated. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
    else:
        st.markdown("### Welcome to the PE CTPA Survey")
        st.markdown(f"We have **{total_cases}** case(s) to evaluate.")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Start Turing Test Evaluation"):
                st.experimental_set_query_params(page="turing_test")
                st.session_state.page = "turing_test"
                st.rerun()
        with col2:
            if st.button("Start AI Report Editing"):
                st.experimental_set_query_params(page="ai_edit")
                st.session_state.page = "ai_edit"
                st.rerun()
        with col3:
            if st.button("Start Standard Evaluation"):
                st.experimental_set_query_params(page="evaluate_case")
                st.session_state.page = "evaluate_case"
                st.rerun()

# --- Main Navigation ---
if st.session_state.page == "index":
    index()
elif st.session_state.page == "evaluate_case":
    evaluate_case()
elif st.session_state.page == "turing_test":
    turing_test()
elif st.session_state.page == "ai_edit":
    ai_edit()
else:
    index()

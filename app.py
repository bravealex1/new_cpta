import streamlit as st
import os
import json
import random
import pandas as pd
import glob

# --------------------------------------------------
# Utility: Save Progress to JSON and CSV
# --------------------------------------------------
# This function already saves based on the category name passed to it.
# e.g., save_progress("turing_test", ...) saves to logs/turing_test_progress.json/csv
#       save_progress("ai_edit", ...) saves to logs/ai_edit_progress.json/csv
def save_progress(category: str, progress: dict):
    """Saves the progress state for a specific category."""
    os.makedirs('logs', exist_ok=True)
    # JSON
    json_path = os.path.join('logs', f"{category}_progress.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
        st.success(f"Progress for '{category}' saved successfully (JSON).")
    except Exception as e:
        st.error(f"Failed to save progress for '{category}' (JSON): {e}")

    # CSV - Append mode requires DataFrame structure to be consistent
    # For simplicity, we'll just save the last state in CSV, or you could load existing
    # and append if you need a history log per category run.
    # The current approach overwrites the CSV with the latest state for that user/session.
    # If you need a history log of *every* save action, more complex logic is needed.
    csv_path = os.path.join('logs', f"{category}_progress.csv")
    try:
        df = pd.DataFrame([progress]) # Save current state as a single row DF
        df.to_csv(csv_path, index=False) # Overwrite or create
        st.success(f"Progress for '{category}' saved successfully (CSV).")
    except Exception as e:
        st.error(f"Failed to save progress for '{category}' (CSV): {e}")


# --------------------------------------------------
# Utility: Save Annotations to JSON
# This function saves annotations per case_id, not per category flow.
# This is separate from the category progress saving.
# --------------------------------------------------
def save_annotations(case_id: str, annotations: list):
    """Saves annotations for a specific case ID."""
    os.makedirs('evaluations', exist_ok=True)
    save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2)
        st.success(f"Annotations for Case {case_id} saved successfully.")
    except Exception as e:
        st.error(f"Failed to save annotations for Case {case_id}: {e}")


# --------------------------------------------------
# 1. Query Parameter Setup
# --------------------------------------------------
query_params = st.experimental_get_query_params()
if "page" in query_params:
    st.session_state.page = query_params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

# --------------------------------------------------
# 2. Initialize Session State
# --------------------------------------------------
def init_state(key, default):
    """Initializes a session state key if it doesn't exist."""
    if key not in st.session_state:
        st.session_state[key] = default

# Initialize states relevant across different pages, but their *values*
# will be managed within each page flow and saved category-specifically.
init_state("last_case", 0)
init_state("assignments", {}) # Used by Turing Test & Standard Eval
init_state("current_slice", 0)
init_state("corrections", []) # Used by Standard Eval & AI Edit (Organ by Organ)
init_state("assembled_report", "") # Used by AI Edit
init_state("turing_test_submitted", False) # Used by Turing Test
init_state("initial_evaluation", None) # Used by Turing Test
init_state("final_evaluation", None) # Used by Turing Test


# --------------------------------------------------
# 3. Define Paths & Cases
# --------------------------------------------------
BASE_IMAGE_DIR = r"2D_Image"
# Ensure the directory exists before listing contents
if not os.path.exists(BASE_IMAGE_DIR):
     st.error(f"Error: Base image directory not found at {BASE_IMAGE_DIR}")
     cases = []
else:
    cases = [f for f in os.listdir(BASE_IMAGE_DIR) if os.path.isdir(os.path.join(BASE_IMAGE_DIR, f))]

total_cases = len(cases)

# --------------------------------------------------
# 4. Helper Functions
# --------------------------------------------------
def load_text_file(file_path):
    """Loads text content from a file, handling missing files."""
    if not os.path.exists(file_path):
        st.warning(f"File not found: {file_path}")
        return ""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        st.error(f"Error reading file {file_path}: {e}")
        return ""


def display_slice_carousel(case_id):
    """Displays image slices for a given case with navigation."""
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    if not os.path.exists(subfolder):
        st.error(f"Case subfolder not found: {subfolder}")
        st.info("No slices found for this case.")
        return [] # Return empty list if subfolder doesn't exist

    images = sorted([os.path.join(subfolder, f)
                     for f in os.listdir(subfolder)
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    total = len(images)
    if total == 0:
        st.info("No slices found for this case.")
        return images # Return empty list if no images found

    # Ensure current_slice is within bounds
    if st.session_state.current_slice >= total:
         st.session_state.current_slice = total - 1
    if st.session_state.current_slice < 0:
         st.session_state.current_slice = 0

    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        if st.button("⟨ Prev", key=f"prev_{case_id}"):
             if st.session_state.current_slice > 0:
                st.session_state.current_slice -= 1
                st.rerun()
    with col2:
        idx = st.session_state.current_slice
        # Add check for valid index
        if 0 <= idx < total:
            st.image(images[idx], width=600)
            st.caption(f"Slice {idx+1} of {total}")
        else:
             st.warning(f"Invalid slice index {idx} for case {case_id}. Total slices: {total}")

    with col3:
        if st.button("Next ⟩", key=f"next_{case_id}"):
            if st.session_state.current_slice < total-1:
                st.session_state.current_slice += 1
                st.rerun()
    return images # Return the list of images


def reset_evaluation():
    """Resets all relevant session state variables for a fresh start."""
    keys_to_reset = [
        "last_case", "assignments", "current_slice", "corrections",
        "assembled_report", "turing_test_submitted", "initial_evaluation", "final_evaluation"
    ]
    for k in keys_to_reset:
        if k in st.session_state:
            del st.session_state[k]
    st.experimental_set_query_params(page="index")
    st.rerun()

# --------------------------------------------------
# 5. Turing Test Page
# --------------------------------------------------
def turing_test():
    """Handles the Turing Test evaluation flow."""
    idx = st.session_state.last_case
    if idx >= total_cases:
        st.markdown("### Turing Test complete. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return
    if not cases: # Handle case where BASE_IMAGE_DIR was empty or not found
         st.warning("No cases available for evaluation.")
         if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
         return

    case_id = cases[idx]
    st.markdown(f"### Turing Test for Case: **{case_id}** (Case {idx+1}/{total_cases})")

    # Save progress button - Saves state specific to Turing Test
    if st.button("Save Progress & Go Back", key=f"save_turing_{case_id}"):
        progress = {
            "last_case": idx,
            "assignments": st.session_state.get("assignments", {}), # Get to avoid error if not set
            "initial_evaluation": st.session_state.get("initial_evaluation"),
            "final_evaluation": st.session_state.get("final_evaluation"), # Include final eval if exists
            "turing_test_submitted": st.session_state.get("turing_test_submitted", False)
        }
        save_progress("turing_test", progress) # Save with category "turing_test"
        # Reset state *only* for the current case flow elements that shouldn't persist on return to index
        # Keep last_case etc. so that the user can resume.
        # The state relevant to the *next* case should be cleared when advancing.
        # No specific state needs clearing here, as last_case handles resume point.
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load text reports
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    gt = load_text_file(os.path.join(subfolder, "text.txt"))
    ai = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Determine assignment order
    # Use case_id instead of idx for assignments key for better clarity/robustness
    assignments = st.session_state.get("assignments", {})
    if case_id not in assignments:
        assign_A = random.choice([True, False])
        assignments[case_id] = assign_A
        st.session_state.assignments = assignments
    else:
        assign_A = assignments[case_id]


    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai
    st.markdown("#### Report A")
    # Add default value to text_area to handle reruns gracefully
    st.text_area("Report A", reportA, height=300, key=f"reportA_tt_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB, height=300, key=f"reportB_tt_{case_id}") # Changed key for uniqueness

    # Initial evaluation (no images yet)
    if st.session_state.get("initial_evaluation") is None:
        st.markdown("### Initial Evaluation (Before Viewing Images)")
        choice = st.radio("Which report is ground truth?",
                          ("Report A", "Report B", "Not sure"), key=f"choice_tt_{case_id}", index=2) # Default to Not sure
        if st.button("Submit Evaluation (Initial - without images)", key=f"submit_initial_tt_{case_id}"):
            st.session_state.initial_evaluation = choice
            st.session_state.turing_test_submitted = True # Flag that initial eval is done
            st.success(f"Initial evaluation recorded: {choice}")
            # No rerun needed here, state change will trigger it if subsequent elements depend on it
            # Or if you want immediate visual update before image section appears.
            # st.rerun() # Optional: uncomment if you want immediate rerun

    # Display images only after initial evaluation is submitted
    if st.session_state.get("turing_test_submitted", False):
        st.markdown("### Evaluation (After Viewing Images)")
        display_slice_carousel(case_id)
        st.markdown(f"**Your initial evaluation was:** {st.session_state.get('initial_evaluation', 'Not submitted yet')}")

        # Allow updating evaluation after viewing images
        # Use different keys for radios to avoid conflicts
        update_option = st.radio("Update Evaluation based on images?",
                                ("Keep my initial evaluation", "Update my evaluation"),
                                key=f"upd_tt_{case_id}", index=0) # Default to Keep

        final_eval_value = st.session_state.get("initial_evaluation") # Default final to initial

        if update_option == "Update my evaluation":
            # Only show the radio if user wants to update
            final_eval_value = st.radio("Select your new evaluation",
                                         ("Report A", "Report B", "Not sure"),
                                         key=f"new_tt_{case_id}", index=2) # Default to Not sure

        # Store the final evaluation in session state
        st.session_state.final_evaluation = final_eval_value


        if st.button("Record Final Evaluation & Continue", key=f"rec_final_tt_{case_id}"):
            # Here you would typically save the final evaluation choice.
            # For this structure, we save the final_evaluation state and advance.
            # If you need a separate file for final evaluations, add save_annotations or similar logic here.
            st.success(f"Final evaluation recorded: {st.session_state.final_evaluation}")

            # Advance to the next case and clear state specific to the *previous* case's evaluation
            st.session_state.last_case = idx + 1
            st.session_state.current_slice = 0
            # Clear state specific to the just-completed case's evaluation flow
            if "initial_evaluation" in st.session_state:
                del st.session_state.initial_evaluation
            if "final_evaluation" in st.session_state:
                 del st.session_state.final_evaluation
            st.session_state.turing_test_submitted = False # Reset flag for the next case

            st.rerun()

# --------------------------------------------------
# 6. Standard Evaluation Page
# --------------------------------------------------
def evaluate_case():
    """Handles the Standard Evaluation flow (AI vs GT, add corrections)."""
    idx = st.session_state.last_case
    if idx >= total_cases:
        st.markdown("### Standard Evaluation complete. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return
    if not cases: # Handle case where BASE_IMAGE_DIR was empty or not found
         st.warning("No cases available for evaluation.")
         if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
         return

    case_id = cases[idx]
    st.markdown(f"### Standard Evaluation for Case: **{case_id}** (Case {idx+1}/{total_cases})")

    # Save progress button - Saves state specific to Standard Evaluation
    if st.button("Save Progress & Go Back", key=f"save_eval_{case_id}"):
        # Filter corrections to save only those relevant to the current case ID
        case_corrs = [c for c in st.session_state.get("corrections", []) if c.get("case_id") == case_id]
        progress = {
            "last_case": idx,
            # Save only the corrections entered *for this specific case*
            "corrections_for_this_case": case_corrs
            # Note: st.session_state.corrections itself holds corrections across cases
            # Saving the full list might be large; saving only current case is better for resume?
            # Let's save the full corrections list in session state, but log only current case's if needed for clarity.
            # For resume, we need the corrections that were *not yet submitted* from previous cases.
            # Let's rethink saving corrections state.
            # Option 1: Save *all* current st.session_state.corrections. This lets you resume adding to the list.
            # Option 2: Only save corrections for the current case. This makes the log file smaller but resume harder if you switch cases before submitting.
            # Let's stick to saving all pending corrections in session state for resume across cases,
            # and filter them only when saving to the specific case's annotation file or showing the table.
        }
        # The actual state needed to *resume* evaluation is st.session_state.corrections
        # when saving progress, we need to include this if we want to resume adding corrections.
        # Let's save the full list of corrections in the standard_evaluation progress file.
        progress["all_pending_corrections"] = st.session_state.get("corrections", [])

        save_progress("standard_evaluation", progress) # Save with category "standard_evaluation"

        # No specific state needs clearing here, as last_case handles resume point.
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load text reports & assignment order
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    gt = load_text_file(os.path.join(subfolder, "text.txt"))
    ai = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Determine assignment order - Use case_id as key
    assignments = st.session_state.get("assignments", {})
    if case_id not in assignments:
        assign_A = random.choice([True, False])
        assignments[case_id] = assign_A
        st.session_state.assignments = assignments
    else:
        assign_A = assignments[case_id]

    reportA = ai if assign_A else gt
    reportB = gt if assign_A else ai
    st.markdown("#### Report A")
    st.text_area("Report A", reportA, height=200, key=f"evalA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB, height=200, key=f"evalB_{case_id}")

    # Display images
    st.markdown("#### Slice Images")
    display_slice_carousel(case_id)

    # Corrections / Annotations section
    st.markdown("#### Corrections / Annotations")
    detected_organs = ["LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
                       "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"]

    # Filter corrections from session state to only show ones for the current case
    case_corrs_display = [c for c in st.session_state.get("corrections", []) if c.get("case_id") == case_id]

    # Input fields for new correction - ensure unique keys per case ID
    with st.form(key=f"correction_form_{case_id}"):
        st.markdown("Add a new correction:")
        selected_organs = [o for o in detected_organs if st.checkbox(o, key=f"org_eval_{case_id}_{o}")]
        organ_to_correct = st.selectbox("Organ to correct", options=selected_organs if selected_organs else ["Select an organ"], key=f"sel_org_eval_{case_id}")
        reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
        reason_for_corr = st.selectbox("Reason", options=reasons, key=f"reason_eval_{case_id}")
        final_reason_text = st.text_input("Specify other reason", key=f"oth_reason_eval_{case_id}", disabled=(reason_for_corr != "Other")) if reason_for_corr == "Other" else reason_for_corr
        detail_text = st.text_area("Correction details", key=f"corr_txt_eval_{case_id}")

        add_correction_button = st.form_submit_button("Add Correction")

        if add_correction_button:
            if organ_to_correct == "Select an organ" and selected_organs:
                 st.warning("Please select an organ to add a correction.")
            elif not detail_text:
                 st.warning("Please provide correction details.")
            else:
                new_correction = {
                    "case_id": case_id,
                    "organ": organ_to_correct,
                    "reason": final_reason_text,
                    "details": detail_text
                }
                # Append the new correction to the session state list
                st.session_state.corrections.append(new_correction)
                st.success("Correction added!")
                # Re-run to update the displayed table and clear the form
                st.rerun()


    # Display existing corrections for this case from session state
    if case_corrs_display:
        st.markdown("### Existing Corrections for this Case:")
        # Display DataFrame excluding the case_id column as it's implied
        corr_df = pd.DataFrame(case_corrs_display).drop(columns=["case_id"])
        st.table(corr_df)

    # Submit button: save annotations (for this case) and advance
    # The evaluation choice is currently not saved persistently by save_annotations
    # If you need to save this choice per case, you would need to modify save_annotations
    # or add a separate saving mechanism for it. For now, it's just selected before proceeding.
    evaluation_choice = st.radio("Select which report is best:",
                                 ("Report A is better", "Report B is better", "Corrected Report is better", "Equivalent"),
                                 key=f"eval_choice_eval_{case_id}", index=3) # Default to Equivalent

    if st.button("Submit Corrections & Continue", key=f"sub_corr_eval_{case_id}"):
        # Get corrections for the current case to save to JSON
        final_case_corrs_to_save = [c for c in st.session_state.get("corrections", []) if c.get("case_id") == case_id]

        # If there are corrections added for this case, save them as annotations
        if final_case_corrs_to_save:
            save_annotations(case_id, final_case_corrs_to_save)
            st.success(f"Annotations saved for case {case_id}.")
        else:
             st.info(f"No new annotations added for case {case_id}. Proceeding.")

        # Optional: Save the final evaluation choice if needed persistently per case
        # Example: save_evaluation_choice(case_id, evaluation_choice)

        # Clear the corrections specifically for the case that was just submitted/processed
        # Keep corrections for other cases that might be pending
        st.session_state.corrections = [c for c in st.session_state.get("corrections", []) if c.get("case_id") != case_id]

        # Advance to the next case
        st.session_state.last_case = idx + 1
        st.session_state.current_slice = 0 # Reset slice index for the next case
        st.rerun()

# --------------------------------------------------
# 7. AI Edit Page
# --------------------------------------------------
def ai_edit():
    """Handles the AI Report Editing flow."""
    idx = st.session_state.last_case
    if idx >= total_cases:
        st.markdown("### All cases have been edited. Thank you!")
        if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
        return
    if not cases: # Handle case where BASE_IMAGE_DIR was empty or not found
         st.warning("No cases available for editing.")
         if st.button("Return to Home"):
            st.experimental_set_query_params(page="index")
            st.session_state.page = "index"
            st.rerun()
         return

    case_id = cases[idx]
    st.markdown(f"### AI Report Editing for Case: **{case_id}** (Case {idx+1}/{total_cases})")

    # Save progress button - Saves state specific to AI Edit
    if st.button("Save Progress & Go Back", key=f"save_ai_{case_id}"):
        progress = {
            "last_case": idx,
            "assembled_report": st.session_state.get("assembled_report", "")
            # If using organ-by-organ corrections, you might want to save st.session_state.corrections here too
            # depending on whether you want to resume adding organ corrections before assembling.
            # For simplicity currently, assembled_report holds the main state to resume editing.
        }
        save_progress("ai_edit", progress) # Save with category "ai_edit"

        # No specific state needs clearing here, as last_case handles resume point.
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

    st.markdown("#### AI Report")
    # Display the original AI report for reference
    st.text_area("Original AI Report", ai_report, height=200, key=f"ai_overview_{case_id}", disabled=True)

    # Display images
    st.markdown("#### Slice Images")
    display_slice_carousel(case_id)


    edit_mode = st.radio("Choose Editing Mode:", ("Free Editing", "Organ-by-Organ Editing"), key=f"mode_ai_{case_id}", index=0) # Default to Free Editing

    final_report_content = "" # Variable to hold the content of the final report text area

    if edit_mode == "Free Editing":
        # Use the 'assembled_report' state to resume free editing if previously saved/assembled
        initial_free_edit_content = st.session_state.get("assembled_report", ai_report)
        final_report_content = st.text_area("Edit the AI-generated report", initial_free_edit_content, height=300, key=f"free_edit_{case_id}")
        # Update assembled_report state as user types in free editing mode
        st.session_state.assembled_report = final_report_content

    else: # Organ-by-Organ Editing
        detected_organs = ["LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
                           "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY", "OTHER FINDINGS"]

        # Filter corrections from session state to only show ones for the current case in this mode
        case_corrs_ai_edit = [c for c in st.session_state.get("corrections", []) if c.get("case_id") == case_id]

        # Input fields for new correction - ensure unique keys per case ID
        with st.form(key=f"correction_form_ai_{case_id}"):
            st.markdown("Add a correction for Organ-by-Organ report:")
            selected_organs_ai = [o for o in detected_organs if st.checkbox(o, key=f"org_ai_{case_id}_{o}")]
            organ_to_correct_ai = st.selectbox("Select an organ to correct", options=selected_organs_ai if selected_organs_ai else ["Select an organ"], key=f"select_ai_{case_id}")
            reasons_ai = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
            reason_for_corr_ai = st.selectbox("Reason", options=reasons_ai, key=f"reason_ai_{case_id}")
            final_reason_text_ai = st.text_input("If Other, specify", key=f"oth_ai_{case_id}", disabled=(reason_for_corr_ai != "Other")) if reason_for_corr_ai == "Other" else reason_for_corr_ai
            detail_text_ai = st.text_area("Correction details", key=f"detail_ai_{case_id}")

            add_correction_button_ai = st.form_submit_button("Add Correction")

            if add_correction_button_ai:
                if organ_to_correct_ai == "Select an organ" and selected_organs_ai:
                    st.warning("Please select an organ to add a correction.")
                elif not detail_text_ai:
                    st.warning("Please provide correction details.")
                else:
                    new_correction_ai = {
                        "case_id": case_id,
                        "organ": organ_to_correct_ai,
                        "reason": final_reason_text_ai,
                        "details": detail_text_ai
                    }
                    # Append the new correction to the session state list
                    st.session_state.corrections.append(new_correction_ai)
                    st.success("Correction added!")
                    # Re-run to update the displayed table and clear the form
                    st.rerun()

        # Display existing corrections for this case from session state
        if case_corrs_ai_edit:
            st.markdown("### Existing Corrections for this Case (Organ-by-Organ):")
            corr_df_ai = pd.DataFrame(case_corrs_ai_edit).drop(columns=["case_id"])
            st.table(corr_df_ai)

        # Button to assemble the report from corrections
        if st.button("Assemble Corrected Report", key=f"assemble_ai_{case_id}"):
            assembled = "Organ-by-Organ Corrected Report:\n\n"
            for c in case_corrs_ai_edit: # Use the filtered list for the current case
                assembled += f"- **{c.get('organ', 'N/A')}**: {c.get('reason', 'N/A')} - {c.get('details', 'No details provided')}\n"
            st.session_state.assembled_report = assembled
            st.success("Corrected report assembled!")
            st.rerun() # Rerun to display the assembled report in the text area

        # Display the assembled report text area
        # Use the 'assembled_report' state for the text area content
        final_report_content = st.text_area("Assembled Corrected Report (Editable)", st.session_state.get("assembled_report", ""), height=300, key=f"assembled_report_ai_{case_id}")
        # Keep assembled_report state updated if user further edits the assembled text
        st.session_state.assembled_report = final_report_content


    # Submit button: Save the final edited report content and advance
    if st.button("Submit Edited Report & Continue", key=f"sub_edit_{case_id}"):
        # You would typically save the 'final_report_content' here.
        # This code does not currently implement saving the final edited report text itself,
        # only the corrections that led to it in Organ-by-Organ mode (if saved via save_annotations
        # or included in save_progress). If you need to save the final free-text report,
        # you would add a save function call here, e.g., save_final_report(case_id, final_report_content).

        st.success("Edited report submitted (This action advances case).")

        # Clear corrections for this case if they were used for assembly/submission
        st.session_state.corrections = [c for c in st.session_state.get("corrections", []) if c.get("case_id") != case_id]
        # Clear the assembled report state for the next case
        st.session_state.assembled_report = ""


        # Advance to the next case
        st.session_state.last_case = idx + 1
        st.session_state.current_slice = 0 # Reset slice index for the next case
        st.rerun()

# --------------------------------------------------
# 8. View All Results Page (NEW)
# --------------------------------------------------
def view_all_results():
    """Displays all saved progress logs and annotations on the main page."""
    st.markdown("## Saved Results from All Categories and Cases")

    if st.button("Return to Home"):
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    st.markdown("---")

    # Display Progress Logs (CSV)
    st.markdown("### Progress Logs (.csv)")
    csv_files = glob.glob("logs/*_progress.csv")
    if not csv_files:
        st.info("No CSV progress logs found in the 'logs/' directory.")
    else:
        for filepath in sorted(csv_files): # Sort for consistent order
            st.markdown(f"**{os.path.basename(filepath)}**")
            try:
                df = pd.read_csv(filepath)
                st.dataframe(df)
            except Exception as e:
                st.warning(f"Failed to read {filepath}: {e}")

    st.markdown("---")

    # Display Annotations (JSON)
    st.markdown("### Annotations (.json)")
    json_files = glob.glob("evaluations/*_annotations.json")
    if not json_files:
        st.info("No JSON annotation files found in the 'evaluations/' directory.")
    else:
        for filepath in sorted(json_files): # Sort for consistent order
            name = os.path.basename(filepath)
            st.markdown(f"**{name}**")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.json(data)
            except Exception as e:
                st.warning(f"Failed to read {filepath}: {e}")

# --------------------------------------------------
# 9. Landing Page & Navigation
# --------------------------------------------------
def index():
    """Landing page with navigation buttons."""
    last = st.session_state.last_case
    if total_cases == 0:
         st.warning("No case directories found in '2D_Image'. Please check the directory path and contents.")
         if st.button("Refresh"):
              st.rerun()
         return

    if last >= total_cases:
        st.markdown("### All selected cases have been evaluated. Thank you!")
        st.balloons() # Celebrate!
        if st.button("Reset Evaluation"):
            reset_evaluation()
    else:
        st.markdown("### Welcome to the Survey")
        st.markdown(f"We have **{total_cases}** case(s) to evaluate.")
        st.markdown(f"You are currently on Case **{last + 1}**.")

        st.markdown("#### Select a Task:")

        c1, c2, c3, c4 = st.columns(4) # Added a column for the new button
        with c1:
            if st.button("Start Turing Test Evaluation"):
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
        with c4: # New column for the results button
             if st.button("View Saved Results"):
                st.experimental_set_query_params(page="view_results")
                st.session_state.page = "view_results"
                st.rerun()

# --------------------------------------------------
# 10. Main Navigation
# --------------------------------------------------
# Route the user based on the current page state
if st.session_state.page == "index":
    index()
elif st.session_state.page == "evaluate_case":
    evaluate_case()
elif st.session_state.page == "turing_test":
    turing_test()
elif st.session_state.page == "ai_edit":
    ai_edit()
elif st.session_state.page == "view_results": # New route for the results page
    view_all_results()
else:
    # Default to index if page state is something unexpected
    st.session_state.page = "index"
    st.experimental_set_query_params(page="index")
    st.rerun() # Rerun to land on the index page properly

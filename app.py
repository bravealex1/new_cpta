<<<<<<< HEAD
# import streamlit as st
# import os
# import json
# import random
# import time
# import pandas as pd

# # --------------------------------------------------
# # 1. Query Parameter Setup
# # --------------------------------------------------
# query_params = st.experimental_get_query_params()
# if "page" in query_params:
#     st.session_state.page = query_params["page"][0]
# elif "page" not in st.session_state:
#     st.session_state.page = "index"

# # --------------------------------------------------
# # 2. Initialize Session State
# # --------------------------------------------------
# if "last_case" not in st.session_state:
#     st.session_state.last_case = 0
# if "assignments" not in st.session_state:
#     st.session_state.assignments = {}
# if "current_slice" not in st.session_state:
#     st.session_state.current_slice = 0

# # Optional: track start time for each "page" so we can measure how long a user spent
# if "start_time" not in st.session_state:
#     st.session_state.start_time = time.time()

# # For storing corrections/annotations
# if "corrections" not in st.session_state:
#     st.session_state["corrections"] = []

# # --------------------------------------------------
# # 3. Define Paths
# # --------------------------------------------------
# BASE_IMAGE_DIR = r"C:\Users\alexvanhalen\OneDrive\Desktop\CPTE_Update\2D_Image"

# # Collect each subfolder in 2D_Image as a "case"
# cases = [
#     f for f in os.listdir(BASE_IMAGE_DIR)
#     if os.path.isdir(os.path.join(BASE_IMAGE_DIR, f))
# ]

# total_cases = len(cases)

# # --------------------------------------------------
# # 4. Helper Functions
# # --------------------------------------------------
# def load_text_file(file_path):
#     """Utility to safely load text from a .txt file."""
#     if not os.path.exists(file_path):
#         return ""
#     with open(file_path, 'r', encoding='utf-8') as f:
#         return f.read()

# def display_slice_carousel(case_id):
#     """
#     Displays images in a carousel-like format (Previous/Next buttons).
#     Assumes all image files are in the subfolder: BASE_IMAGE_DIR / case_id
#     """
#     subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
#     # Collect images (any extension you like: .png, .jpg, .jpeg, etc.)
#     all_files = os.listdir(subfolder)
#     slice_images = [
#         os.path.join(subfolder, f) for f in all_files
#         if f.lower().endswith(('.png', '.jpg', '.jpeg'))
#     ]
#     slice_images.sort()

#     total_slices = len(slice_images)
#     if total_slices == 0:
#         st.info("No slices found for this case.")
#         return

#     col1, col2, col3 = st.columns([1, 8, 1])
#     with col1:
#         if st.button("⟨ Prev", key=f"prev_{case_id}"):
#             if st.session_state.current_slice > 0:
#                 st.session_state.current_slice -= 1
#                 st.rerun()
#     with col2:
#         current_index = st.session_state.current_slice
#         st.image(slice_images[current_index], width=600)
#         st.caption(f"Slice {current_index + 1} of {total_slices}")
#     with col3:
#         if st.button("Next ⟩", key=f"next_{case_id}"):
#             if st.session_state.current_slice < total_slices - 1:
#                 st.session_state.current_slice += 1
#                 st.rerun()

# def save_annotations(case_id, annotations):
#     """
#     Saves annotations to a JSON file. 
#     Adjust as needed for your environment.
#     """
#     os.makedirs('evaluations', exist_ok=True)
#     save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
#     with open(save_path, 'w') as f:
#         json.dump(annotations, f, indent=2)

# def reset_evaluation():
#     """Clears session state for a fresh start."""
#     for key in list(st.session_state.keys()):
#         del st.session_state[key]
#     st.experimental_set_query_params(page="index")
#     st.rerun()

# # --------------------------------------------------
# # 5. Turing Test Page
# #    - Show pred.txt vs. text.txt in random order
# # --------------------------------------------------
# def turing_test():
#     case_index = st.session_state.last_case

#     if case_index >= total_cases:
#         st.markdown("### Turing Test complete. Thank you!")
#         if st.button("Return to Home"):
#             st.experimental_set_query_params(page="index")
#             st.session_state.page = "index"
#             st.rerun()
#         return

#     case_id = cases[case_index]
#     st.markdown(f"### Turing Test for Case: **{case_id}** (Case {case_index+1} of {total_cases})")

#     # Load text
#     subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
#     ground_truth_report = load_text_file(os.path.join(subfolder, "text.txt"))
#     ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

#     # Decide which text to show as "Report A" or "Report B"
#     assignments = st.session_state.get('assignments', {})
#     if str(case_index) in assignments:
#         assign_A = assignments[str(case_index)]
#     else:
#         assign_A = random.choice([True, False])
#         assignments[str(case_index)] = assign_A
#         st.session_state.assignments = assignments

#     if assign_A:
#         reportA_text = ai_report
#         reportB_text = ground_truth_report
#     else:
#         reportA_text = ground_truth_report
#         reportB_text = ai_report

#     # Show text areas
#     st.markdown("#### Report A")
#     st.text_area("Report A", reportA_text, height=300, key=f"reportA_{case_id}")
#     st.markdown("#### Report B")
#     st.text_area("Report B", reportB_text, height=300, key=f"reportB_{case_id}")

#     # Show images if desired
#     show_images = st.checkbox("Show slice images", value=True, key=f"show_images_{case_id}")
#     if show_images:
#         st.markdown("#### Slice Images")
#         display_slice_carousel(case_id)

#     # Let user guess which is which or which is better
#     choice = st.radio(
#         "Which report is ground truth?",
#         ("Report A", "Report B", "Not sure"),
#         key=f"choice_{case_id}"
#     )

#     if st.button("Submit Turing Test Evaluation", key=f"submit_turing_{case_id}"):
#         # Optional: store the choice somewhere
#         st.success(f"Submitted evaluation: {choice}")
#         # Move to next case
#         st.session_state.last_case = case_index + 1
#         st.session_state.current_slice = 0
#         st.rerun()

# # --------------------------------------------------
# # 6. Standard Evaluation Page
# #    - Radiologist reviews pred.txt vs. text.txt
# #    - Adds notes/corrections
# # --------------------------------------------------
# def evaluate_case():
#     case_index = st.session_state.last_case

#     if case_index >= total_cases:
#         st.markdown("### Evaluation complete. Thank you!")
#         if st.button("Reset Evaluation"):
#             reset_evaluation()
#         return

#     case_id = cases[case_index]
#     st.markdown(f"### Evaluating Case: **{case_id}** (Case {case_index+1} of {total_cases})")

#     # Load text
#     subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
#     ground_truth_report = load_text_file(os.path.join(subfolder, "text.txt"))
#     ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

#     # Show them side by side or in random order
#     assignments = st.session_state.get('assignments', {})
#     if str(case_index) in assignments:
#         assign_A = assignments[str(case_index)]
#     else:
#         assign_A = random.choice([True, False])
#         assignments[str(case_index)] = assign_A
#         st.session_state.assignments = assignments

#     if assign_A:
#         reportA_text = ai_report
#         reportB_text = ground_truth_report
#     else:
#         reportA_text = ground_truth_report
#         reportB_text = ai_report

#     st.markdown("#### Report A")
#     st.text_area("Report A", reportA_text, height=200, key=f"reportA_{case_id}")
#     st.markdown("#### Report B")
#     st.text_area("Report B", reportB_text, height=200, key=f"reportB_{case_id}")

#     # Display images
#     st.markdown("#### Slice Images")
#     display_slice_carousel(case_id)

#     # Let the radiologist add corrections or notes
#     st.markdown("#### Corrections / Annotations")
#     detected_organs = [
#         "LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
#         "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY",
#         "OTHER FINDINGS"
#     ]
#     st.write("Select the organs you want to correct:")
#     selected_organs = [
#         organ for organ in detected_organs
#         if st.checkbox(organ, key=f"organ_{case_id}_{organ}")
#     ]

#     if selected_organs:
#         st.write("Enter correction details:")
#         organ_to_correct = st.selectbox(
#             "Organ to correct", options=selected_organs, key=f"organ_select_{case_id}"
#         )
#         predefined_reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
#         reason_choice = st.selectbox(
#             "Reason for disagreement", options=predefined_reasons, key=f"reason_choice_{case_id}"
#         )
#         final_reason = (
#             st.text_input("Specify other reason", key=f"reason_text_{case_id}")
#             if reason_choice == "Other"
#             else reason_choice
#         )
#         correction_text = st.text_area("Correction details", key=f"correction_text_{case_id}")

#         if st.button("Add Correction", key=f"add_correction_{case_id}"):
#             new_correction = {
#                 "case_id": case_id,
#                 "organ": organ_to_correct,
#                 "reason": final_reason,
#                 "details": correction_text
#             }
#             st.session_state["corrections"].append(new_correction)
#             st.success("Correction added!")
#             st.rerun()

#     # Display existing corrections for this case
#     case_corrections = [
#         c for c in st.session_state["corrections"] if c["case_id"] == case_id
#     ]
#     if case_corrections:
#         st.markdown("#### Current Corrections for This Case")
#         corrections_df = pd.DataFrame(case_corrections)
#         st.table(corrections_df.drop(columns=["case_id"]))

#     # Submit button
#     if st.button("Submit All Corrections", key=f"submit_corrections_{case_id}"):
#         try:
#             # Save to JSON (if you want a separate file for each case)
#             save_annotations(case_id, case_corrections)
#             st.success("Annotations saved.")
#             # Clear local corrections from memory
#             st.session_state["corrections"] = [
#                 c for c in st.session_state["corrections"] if c["case_id"] != case_id
#             ]
#             st.session_state.last_case = case_index + 1
#             st.session_state.current_slice = 0
#             st.rerun()
#         except Exception as e:
#             st.error(f"Failed to save annotations: {e}")

# # --------------------------------------------------
# # 7. AI Edit Page (optional)
# # --------------------------------------------------
# def ai_edit():
#     case_index = st.session_state.last_case

#     if case_index >= total_cases:
#         st.markdown("### All cases have been edited. Thank you!")
#         if st.button("Return to Home"):
#             st.experimental_set_query_params(page="index")
#             st.session_state.page = "index"
#             st.rerun()
#         return

#     case_id = cases[case_index]
#     subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
#     ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

#     st.markdown(f"### AI Report Editing for Case: **{case_id}** (Case {case_index+1} of {total_cases})")
#     st.markdown("#### AI Report")
#     edited_report = st.text_area("Edit the AI-generated report", ai_report, height=300, key=f"ai_edit_{case_id}")

#     # (Optional) Show images for reference
#     st.markdown("#### Slice Images")
#     display_slice_carousel(case_id)

#     if st.button("Submit Edited Report", key=f"submit_edit_{case_id}"):
#         st.success("Edited report submitted.")
#         # Here you could save the edited report to file or database
#         # e.g., save_annotations(case_id, {"edited_ai_report": edited_report})
#         st.session_state.last_case = case_index + 1
#         st.session_state.current_slice = 0
#         st.rerun()

# # --------------------------------------------------
# # 8. Landing Page
# # --------------------------------------------------
# def index():
#     last_case = st.session_state.last_case
#     if last_case >= total_cases:
#         st.markdown("### All selected cases have been evaluated. Thank you!")
#         if st.button("Reset Evaluation"):
#             reset_evaluation()
#     else:
#         st.markdown("### Welcome to the Survey")
#         st.markdown(f"We have **{total_cases}** case(s) to evaluate.")
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             if st.button("Start Turing Test Evaluation"):
#                 st.experimental_set_query_params(page="turing_test")
#                 st.session_state.page = "turing_test"
#                 st.rerun()
#         with col2:
#             if st.button("Start AI Report Editing"):
#                 st.experimental_set_query_params(page="ai_edit")
#                 st.session_state.page = "ai_edit"
#                 st.rerun()
#         with col3:
#             if st.button("Start Standard Evaluation"):
#                 st.experimental_set_query_params(page="evaluate_case")
#                 st.session_state.page = "evaluate_case"
#                 st.rerun()

# # --------------------------------------------------
# # 9. Main Navigation
# # --------------------------------------------------
# if st.session_state.page == "index":
#     index()
# elif st.session_state.page == "evaluate_case":
#     evaluate_case()
# elif st.session_state.page == "turing_test":
#     turing_test()
# elif st.session_state.page == "ai_edit":
#     ai_edit()
# else:
#     index()


=======
>>>>>>> ebfbba259d47bfae9068c999e27062b76e43948e
import streamlit as st 
import os
import json
import random
import time
import pandas as pd

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
if "last_case" not in st.session_state:
    st.session_state.last_case = 0
if "assignments" not in st.session_state:
    st.session_state.assignments = {}
if "current_slice" not in st.session_state:
    st.session_state.current_slice = 0
if "corrections" not in st.session_state:
    st.session_state["corrections"] = []
# For storing assembled report from organ-by-organ editing in AI edit page
if "assembled_report" not in st.session_state:
    st.session_state["assembled_report"] = ""
# Flag for Turing Test evaluation submission
if "turing_test_submitted" not in st.session_state:
    st.session_state.turing_test_submitted = False
# --------------------------------------------------
# 3. Define Paths
# --------------------------------------------------
<<<<<<< HEAD
BASE_IMAGE_DIR = r"C:\Users\alexvanhalen\OneDrive\Desktop\CPTE_Update\2D_Image"
=======
BASE_IMAGE_DIR = r"2D_Image"
>>>>>>> ebfbba259d47bfae9068c999e27062b76e43948e
cases = [f for f in os.listdir(BASE_IMAGE_DIR)
         if os.path.isdir(os.path.join(BASE_IMAGE_DIR, f))]
total_cases = len(cases)

# --------------------------------------------------
# 4. Helper Functions
# --------------------------------------------------
def load_text_file(file_path):
    """Utility to safely load text from a .txt file."""
    if not os.path.exists(file_path):
        return ""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def display_slice_carousel(case_id):
    """
    Displays images in a carousel-like format (Previous/Next buttons).
    Assumes all image files are in the subfolder: BASE_IMAGE_DIR / case_id.
    """
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    all_files = os.listdir(subfolder)
    slice_images = [os.path.join(subfolder, f) for f in all_files
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    slice_images.sort()
    total_slices = len(slice_images)
    if total_slices == 0:
        st.info("No slices found for this case.")
        return
    col1, col2, col3 = st.columns([1, 8, 1])
    with col1:
        if st.button("⟨ Prev", key=f"prev_{case_id}"):
            if st.session_state.current_slice > 0:
                st.session_state.current_slice -= 1
                st.rerun()
    with col2:
        current_index = st.session_state.current_slice
        st.image(slice_images[current_index], width=600)
        st.caption(f"Slice {current_index + 1} of {total_slices}")
    with col3:
        if st.button("Next ⟩", key=f"next_{case_id}"):
            if st.session_state.current_slice < total_slices - 1:
                st.session_state.current_slice += 1
                st.rerun()

def save_annotations(case_id, annotations):
    """
    Saves annotations to a JSON file.
    Adjust as needed for your environment.
    """
    os.makedirs('evaluations', exist_ok=True)
    save_path = os.path.join('evaluations', f"{case_id}_annotations.json")
    with open(save_path, 'w') as f:
        json.dump(annotations, f, indent=2)

def reset_evaluation():
    """Clears session state for a fresh start."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_set_query_params(page="index")
    st.rerun()

# --------------------------------------------------
# 5. Turing Test Page
#    - Show pred.txt vs. text.txt in random order,
#      with image reveal on re-evaluation.
# --------------------------------------------------
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
    st.markdown(f"### Turing Test for Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    
    # Display a global "Save Progress & Go Back" button
    if st.button("Save Progress & Go Back", key=f"go_back_global_turing_{case_id}"):
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load text files for reports
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    ground_truth_report = load_text_file(os.path.join(subfolder, "text.txt"))
    ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Determine assignment order for which report is labeled A/B.
    assignments = st.session_state.get('assignments', {})
    if str(case_index) in assignments:
        assign_A = assignments[str(case_index)]
    else:
        assign_A = random.choice([True, False])
        assignments[str(case_index)] = assign_A
        st.session_state.assignments = assignments

    if assign_A:
        reportA_text = ai_report
        reportB_text = ground_truth_report
    else:
        reportA_text = ground_truth_report
        reportB_text = ai_report

    st.markdown("#### Report A")
    st.text_area("Report A", reportA_text, height=300, key=f"reportA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB_text, height=300, key=f"reportB_{case_id}")

    # -------------------------------
    # Initial Evaluation (no images)
    # -------------------------------
    if "initial_evaluation" not in st.session_state:
        evaluation_choice = st.radio("Which report is ground truth?",
                                     ("Report A", "Report B", "Not sure"),
                                     key=f"choice_{case_id}")
        if st.button("Submit Evaluation (Initial - without images)", key=f"submit_initial_{case_id}"):
            st.session_state.initial_evaluation = evaluation_choice
            st.session_state.turing_test_submitted = True
            st.success(f"Initial evaluation recorded: {evaluation_choice}")
            st.rerun()
    else:
        st.markdown("### Evaluation (After Viewing Images)")
        # --------------------------------------
        # Re-Evaluation after images are shown:
        # --------------------------------------
        st.markdown("#### Slice Images for Re-Evaluation")
        display_slice_carousel(case_id)
        
        st.markdown(f"**Your initial evaluation was:** {st.session_state.initial_evaluation}")
        st.markdown("Would you like to update your evaluation after viewing the images?")
        update_choice = st.radio("Update Evaluation", 
                                 ("Keep my initial evaluation", "Update my evaluation"),
                                 key=f"update_choice_{case_id}")
        if update_choice == "Update my evaluation":
            new_evaluation = st.radio("Select your new evaluation", 
                                      ("Report A", "Report B", "Not sure"),
                                      key=f"new_choice_{case_id}")
        else:
            new_evaluation = st.session_state.initial_evaluation

        if st.button("Record Final Evaluation", key=f"record_final_{case_id}"):
            st.session_state.final_evaluation = new_evaluation
            st.success(f"Final evaluation recorded: {st.session_state.final_evaluation}")

        if st.button("Continue to Next Case", key=f"continue_{case_id}"):
            # Optionally, you can save both the initial and final evaluations to file here.
            st.session_state.last_case = case_index + 1
            st.session_state.current_slice = 0
            # Clear the evaluation responses so the next case starts fresh
            del st.session_state.initial_evaluation
            if "final_evaluation" in st.session_state:
                del st.session_state.final_evaluation
            st.session_state.turing_test_submitted = False
            st.rerun()

# --------------------------------------------------
# 6. Standard Evaluation Page
#    - Radiologist reviews reports, adds corrections,
#      and (if available) evaluates a corrected report.
# --------------------------------------------------
def evaluate_case():
    case_index = st.session_state.last_case
    if case_index >= total_cases:
        st.markdown("### Evaluation complete. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
        return

    case_id = cases[case_index]
    st.markdown(f"### Evaluating Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    
    # Global "Save Progress & Go Back" button
    if st.button("Save Progress & Go Back", key=f"go_back_global_eval_{case_id}"):
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()

    # Load text reports
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    ground_truth_report = load_text_file(os.path.join(subfolder, "text.txt"))
    ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))

    # Determine assignment order
    assignments = st.session_state.get('assignments', {})
    if str(case_index) in assignments:
        assign_A = assignments[str(case_index)]
    else:
        assign_A = random.choice([True, False])
        assignments[str(case_index)] = assign_A
        st.session_state.assignments = assignments

    if assign_A:
        reportA_text = ai_report
        reportB_text = ground_truth_report
    else:
        reportA_text = ground_truth_report
        reportB_text = ai_report

    st.markdown("#### Report A")
    st.text_area("Report A", reportA_text, height=200, key=f"eval_reportA_{case_id}")
    st.markdown("#### Report B")
    st.text_area("Report B", reportB_text, height=200, key=f"eval_reportB_{case_id}")

    # If an assembled corrected report exists (from organ-by-organ editing), show it.
    assembled_report = st.session_state.get("assembled_report", "")
    if assembled_report:
        st.markdown("#### Corrected Report (from Organ-by-Organ Editing)")
        st.text_area("Corrected Report", assembled_report, height=200, key=f"eval_corrected_{case_id}")
        eval_options = ("Report A is better", "Report B is better", "Corrected Report is better", "Equivalent")
    else:
        eval_options = ("Report A is better", "Report B is better", "Equivalent")
    evaluation_choice = st.radio("Select which report is best:", eval_options, key=f"eval_choice_{case_id}")

    # Display images (always visible in evaluation)
    st.markdown("#### Slice Images")
    display_slice_carousel(case_id)

    # Corrections / Annotations section
    st.markdown("#### Corrections / Annotations")
    detected_organs = [
        "LIVER", "PORTAL VEIN", "INTRAHEPATIC IVC", "INTRAHEPATIC BILE DUCTS",
        "COMMON BILE DUCT", "GALLBLADDER", "PANCREAS", "RIGHT KIDNEY",
        "OTHER FINDINGS"
    ]
    st.write("Select the organs you want to correct:")
    selected_organs = [organ for organ in detected_organs
                       if st.checkbox(organ, key=f"organ_{case_id}_{organ}")]
    if selected_organs:
        st.write("Enter correction details:")
        organ_to_correct = st.selectbox("Organ to correct", options=selected_organs, key=f"organ_select_{case_id}")
        predefined_reasons = ["Measurement error", "Misinterpretation", "Missing finding", "Other"]
        reason_choice = st.selectbox("Reason for disagreement", options=predefined_reasons, key=f"reason_choice_{case_id}")
        final_reason = st.text_input("Specify other reason", key=f"reason_text_{case_id}") if reason_choice == "Other" else reason_choice
        correction_text = st.text_area("Correction details", key=f"correction_text_{case_id}")
        if st.button("Add Correction", key=f"add_correction_{case_id}"):
            new_correction = {
                "case_id": case_id,
                "organ": organ_to_correct,
                "reason": final_reason,
                "details": correction_text
            }
            st.session_state["corrections"].append(new_correction)
            st.success("Correction added!")
            st.rerun()

    # Display existing corrections for this case
    case_corrections = [c for c in st.session_state["corrections"] if c["case_id"] == case_id]
    if case_corrections:
        st.markdown("#### Current Corrections for This Case")
        corrections_df = pd.DataFrame(case_corrections)
        st.table(corrections_df.drop(columns=["case_id"]))

    # Submit button: save annotations and evaluation choice
    if st.button("Submit All Corrections", key=f"submit_corrections_{case_id}"):
        try:
            # Optionally, evaluation_choice can be saved along with annotations
            save_annotations(case_id, case_corrections)
            st.success(f"Annotations saved. Evaluation: {evaluation_choice}")
            # Clear corrections for this case
            st.session_state["corrections"] = [c for c in st.session_state["corrections"] if c["case_id"] != case_id]
            st.session_state.last_case = case_index + 1
            st.session_state.current_slice = 0
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save annotations: {e}")

# --------------------------------------------------
# 7. AI Edit Page (optional)
#    - Radiologist can freely edit the AI report or use organ-by-organ editing.
# --------------------------------------------------
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
    subfolder = os.path.join(BASE_IMAGE_DIR, case_id)
    ai_report = load_text_file(os.path.join(subfolder, "pred.txt"))
    st.markdown(f"### AI Report Editing for Case: **{case_id}** (Case {case_index+1} of {total_cases})")
    
    # Global "Save Progress & Go Back" button
    if st.button("Save Progress & Go Back", key=f"go_back_global_ai_{case_id}"):
        st.experimental_set_query_params(page="index")
        st.session_state.page = "index"
        st.rerun()
    
    st.markdown("#### AI Report")
    st.text_area("AI Report", ai_report, height=200, key=f"ai_report_overview_{case_id}")
    
    # Select editing mode: free editing or organ-by-organ editing
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
                    assembled = "Organ-by-Organ Corrected Report:\n\n"
                    for corr in st.session_state["corrections"]:
                        assembled += f"{corr['organ']}: {corr['reason']} - {corr['details']}\n\n"
                    st.session_state["assembled_report"] = assembled
                    st.success("Corrected report assembled!")
                    st.rerun()
        final_report = st.session_state.get("assembled_report", "")
    
    if st.button("Submit Edited Report", key=f"submit_edit_{case_id}"):
        st.success("Edited report submitted.")
        # Optionally, save the final report as needed.
        st.session_state.last_case = case_index + 1
        st.session_state.current_slice = 0
        st.rerun()

# --------------------------------------------------
# 8. Landing Page
# --------------------------------------------------
def index():
    last_case = st.session_state.last_case
    if last_case >= total_cases:
        st.markdown("### All selected cases have been evaluated. Thank you!")
        if st.button("Reset Evaluation"):
            reset_evaluation()
    else:
        st.markdown("### Welcome to the Survey")
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

# --------------------------------------------------
# 9. Main Navigation
# --------------------------------------------------
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


# API Key: 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
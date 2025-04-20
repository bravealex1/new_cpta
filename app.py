import streamlit as st
import os
import json
import uuid
import random
import pandas as pd
import glob

# --------------------------------------------------
# 0. Generate & Store Unique Session ID
# --------------------------------------------------
if "session_id" not in st.session_state:
    # Version 4 UUID gives a random 128‑bit ID
    st.session_state.session_id = str(uuid.uuid4())

# --------------------------------------------------
# Sidebar: Display Session ID
# --------------------------------------------------
st.sidebar.markdown(f"**Session ID:** `{st.session_state.session_id}`")

# --------------------------------------------------
# Utility: Save Progress per Category & Session
# --------------------------------------------------
def save_progress(category: str, progress: dict):
    os.makedirs("logs", exist_ok=True)  # ensure logs dir exists :contentReference[oaicite:7]{index=7}
    sid = st.session_state.session_id

    # JSON
    jpath = os.path.join("logs", f"{category}_{sid}_progress.json")
    with open(jpath, "w") as f:
        json.dump(progress, f, indent=2)

    # CSV (overwrite latest)
    cpath = os.path.join("logs", f"{category}_{sid}_progress.csv")
    pd.DataFrame([progress]).to_csv(cpath, index=False)

# --------------------------------------------------
# Utility: Save Annotations per Case
# --------------------------------------------------
def save_annotations(case_id: str, annotations: list):
    os.makedirs("evaluations", exist_ok=True)
    path = os.path.join("evaluations", f"{case_id}_annotations.json")
    with open(path, "w") as f:
        json.dump(annotations, f, indent=2)

# --------------------------------------------------
# Initialize per‑workflow Session State
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
# Routing Setup
# --------------------------------------------------
params = st.experimental_get_query_params()
if "page" in params:
    st.session_state.page = params["page"][0]
elif "page" not in st.session_state:
    st.session_state.page = "index"

BASE_IMAGE_DIR = "2D_Image"
cases = sorted(d for d in os.listdir(BASE_IMAGE_DIR) if os.path.isdir(os.path.join(BASE_IMAGE_DIR, d)))
total_cases = len(cases)

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def load_text(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

def display_carousel(category, case_id):
    key = f"current_slice_{category}"
    folder = os.path.join(BASE_IMAGE_DIR, case_id)
    images = sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ) if os.path.exists(folder) else []
    if not images:
        st.info("No images.")
        return

    idx = st.session_state[key]
    idx = max(0, min(idx, len(images) - 1))
    st.session_state[key] = idx

    c1, c2, c3 = st.columns([1, 8, 1])
    with c1:
        if st.button("⟨ Prev", key=f"prev_{category}_{case_id}") and idx > 0:
            st.session_state[key] -= 1
            st.rerun()
    with c2:
        st.image(images[idx], width=500)
        st.caption(f"Slice {idx+1} / {len(images)}")
    with c3:
        if st.button("Next ⟩", key=f"next_{category}_{case_id}") and idx < len(images)-1:
            st.session_state[key] += 1
            st.rerun()

# --------------------------------------------------
# Pages
# --------------------------------------------------
def index():
    st.title("Survey App")
    if total_cases == 0:
        st.error("No cases found.")
        return

    # Show progress for each workflow :contentReference[oaicite:8]{index=8}
    st.markdown("### Your Progress")
    st.markdown(f"- **Turing Test**: Case {st.session_state.last_case_turing+1}/{total_cases}")
    st.markdown(f"- **Standard Eval**: Case {st.session_state.last_case_standard+1}/{total_cases}")
    st.markdown(f"- **AI Edit**: Case {st.session_state.last_case_ai+1}/{total_cases}")

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Turing Test"):
        st.experimental_set_query_params(page="turing_test")
        st.session_state.page = "turing_test"
        st.rerun()
    if c2.button("Standard Eval"):
        st.experimental_set_query_params(page="standard_eval")
        st.session_state.page = "standard_eval"
        st.rerun()
    if c3.button("AI Report Edit"):
        st.experimental_set_query_params(page="ai_edit")
        st.session_state.page = "ai_edit"
        st.rerun()
    if c4.button("View All Results"):
        st.experimental_set_query_params(page="view_results")
        st.session_state.page = "view_results"
        st.rerun()

def turing_test():
    idx = st.session_state.last_case_turing
    if idx >= total_cases:
        st.success("Turing Test complete!")
        if st.button("Home"):
            st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"Turing Test: {case} ({idx+1}/{total_cases})")

    if st.button("Save & Back"):
        prog = {
            "last_case": idx,
            "assignments": st.session_state.assignments_turing,
            "initial_eval": st.session_state.initial_eval_turing,
            "final_eval": st.session_state.final_eval_turing,
            "viewed_images": st.session_state.viewed_images_turing
        }
        save_progress("turing_test", prog)
        st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()

    # Load & display A vs B
    gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
    ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    assigns = st.session_state.assignments_turing
    if case not in assigns:
        assigns[case] = random.choice([True, False])
        st.session_state.assignments_turing = assigns
    A, B = (ai, gt) if assigns[case] else (gt, ai)
    st.subheader("Report A"); st.text_area("A", A, height=200, key=f"A_t_{case}")
    st.subheader("Report B"); st.text_area("B", B, height=200, key=f"B_t_{case}")

    # Initial evaluation
    if st.session_state.initial_eval_turing is None:
        choice = st.radio("Which is GT?", ["A","B","Not sure"], key=f"ch_t_{case}", index=2)
        if st.button("Submit Initial"):
            st.session_state.initial_eval_turing = choice
            st.session_state.viewed_images_turing = True
            st.success("Recorded initial eval.")
            st.rerun()

    # After images
    if st.session_state.viewed_images_turing:
        st.markdown("#### Images")
        display_carousel("turing", case)
        st.markdown(f"**Initial Eval:** {st.session_state.initial_eval_turing}")
        up = st.radio("Keep or Update?", ["Keep","Update"], key=f"up_t_{case}")
        final = st.session_state.initial_eval_turing
        if up=="Update":
            final = st.radio("New choice:", ["A","B","Not sure"], key=f"new_t_{case}", index=2)
        st.session_state.final_eval_turing = final
        if st.button("Finalize & Next"):
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
            st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"Standard Eval: {case} ({idx+1}/{total_cases})")

    if st.button("Save & Back"):
        prog = {
            "last_case": idx,
            "assignments": st.session_state.assignments_standard,
            "corrections": st.session_state.corrections_standard
        }
        save_progress("standard_evaluation", prog)
        st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()

    # A vs B
    gt = load_text(os.path.join(BASE_IMAGE_DIR, case, "text.txt"))
    ai = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    assigns = st.session_state.assignments_standard
    if case not in assigns:
        assigns[case] = random.choice([True, False])
        st.session_state.assignments_standard = assigns
    A, B = (ai, gt) if assigns[case] else (gt, ai)
    st.subheader("Report A"); st.text_area("A", A, height=150, key=f"A_s_{case}")
    st.subheader("Report B"); st.text_area("B", B, height=150, key=f"B_s_{case}")
    st.markdown("#### Images"); display_carousel("standard", case)

    # Corrections
    organ = st.selectbox("Organ", [""]+["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_s_{case}")
    reason = st.text_input("Reason", key=f"rsn_s_{case}")
    details = st.text_area("Details", key=f"dtl_s_{case}")
    if st.button("Add Corr") and organ:
        st.session_state.corrections_standard.append({
            "case_id": case, "organ": organ,
            "reason": reason, "details": details
        })
        st.success("Added correction"); st.rerun()

    cors = [c for c in st.session_state.corrections_standard if c["case_id"]==case]
    if cors:
        st.table(pd.DataFrame(cors).drop(columns=["case_id"]))

    choice = st.radio("Best report?", ["A","B","Corrected","Equal"], key=f"ch_s_{case}")
    if st.button("Submit & Next"):
        if cors:
            save_annotations(case, cors)
        st.session_state.corrections_standard = [c for c in st.session_state.corrections_standard if c["case_id"]!=case]
        st.session_state.last_case_standard += 1
        st.session_state.current_slice_standard = 0
        st.rerun()

def ai_edit():
    idx = st.session_state.last_case_ai
    if idx >= total_cases:
        st.success("AI Edit complete!")
        if st.button("Home"):
            st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()
        return
    case = cases[idx]
    st.header(f"AI Edit: {case} ({idx+1}/{total_cases})")

    if st.button("Save & Back"):
        prog = {
            "last_case": idx,
            "assembled": st.session_state.assembled_ai,
            "corrections": st.session_state.corrections_ai
        }
        save_progress("ai_edit", prog)
        st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()

    orig = load_text(os.path.join(BASE_IMAGE_DIR, case, "pred.txt"))
    st.subheader("Original AI Report"); st.text_area("orig", orig, height=150, disabled=True)
    st.markdown("#### Images"); display_carousel("ai", case)

    mode = st.radio("Mode", ["Free","Organ"], key=f"md_ai_{case}")
    if mode=="Free":
        text = st.session_state.assembled_ai or orig
        new = st.text_area("Edit", text, height=200, key=f"free_ai_{case}")
        st.session_state.assembled_ai = new
    else:
        organ = st.selectbox("Organ", [""]+["LIVER","PANCREAS","KIDNEY","OTHER"], key=f"org_ai_{case}")
        reason = st.text_input("Reason", key=f"rsn_ai_{case}")
        details = st.text_area("Details", key=f"dtl_ai_{case}")
        if st.button("Add Corr AI") and organ:
            st.session_state.corrections_ai.append({
                "case_id": case, "organ": organ,
                "reason": reason, "details": details
            })
            st.success("Added"); st.rerun()

        cors = [c for c in st.session_state.corrections_ai if c["case_id"]==case]
        if cors:
            st.table(pd.DataFrame(cors).drop(columns=["case_id"]))
            if st.button("Assemble"):
                txt = "\n".join(f"- {c['organ']}: {c['reason']} — {c['details']}" for c in cors)
                st.session_state.assembled_ai = txt
                st.success("Assembled"); st.rerun()

    if st.button("Submit & Next"):
        st.session_state.corrections_ai = [c for c in st.session_state.corrections_ai if c["case_id"]!=case]
        st.session_state.assembled_ai = ""
        st.session_state.last_case_ai += 1
        st.session_state.current_slice_ai = 0
        st.rerun()

def view_all_results():
    st.title("All Saved Results")
    if st.button("Home"):
        st.session_state.page = "index"; st.experimental_set_query_params(page="index"); st.rerun()

    st.subheader("Turing Test Logs")
    for fp in sorted(glob.glob("logs/turing_test_*_progress.csv")):
        st.markdown(f"**{os.path.basename(fp)}**")
        st.dataframe(pd.read_csv(fp))

    st.subheader("Standard Eval Logs")
    for fp in sorted(glob.glob("logs/standard_evaluation_*_progress.csv")):
        st.markdown(f"**{os.path.basename(fp)}**")
        st.dataframe(pd.read_csv(fp))

    st.subheader("AI Edit Logs")
    for fp in sorted(glob.glob("logs/ai_edit_*_progress.csv")):
        st.markdown(f"**{os.path.basename(fp)}**")
        st.dataframe(pd.read_csv(fp))

# --------------------------------------------------
# Main Router
# --------------------------------------------------
page = st.session_state.page
if page == "turing_test":
    turing_test()
elif page == "standard_eval":
    evaluate_case()
elif page == "ai_edit":
    ai_edit()
elif page == "view_results":
    view_all_results()
else:
    index()

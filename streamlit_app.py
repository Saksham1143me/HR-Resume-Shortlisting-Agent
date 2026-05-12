import sys
import os
import tempfile
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.pipeline import run_pipeline
from agents.humaninloop import apply_hr_override, get_override_log
from utils import config 
from typing import Optional

st.set_page_config(
    page_title="HR Resume Shortlisting Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .metric-card {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.08); text-align: center;
  }
  .hire-badge  { background:#d1fae5; color:#065f46; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
  .maybe-badge { background:#fef3c7; color:#92400e; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
  .no-badge    { background:#fee2e2; color:#b91c1c; padding:4px 12px; border-radius:20px; font-weight:700; font-size:13px; }
  .section-header { font-size:20px; font-weight:800; color:#1e1b4b; margin-bottom:16px; }
</style>
""", unsafe_allow_html=True)


with st.sidebar:
    st.image("https://img.icons8.com/color/96/recruitment.png", width=60)
    st.title("HR Agent")
    st.caption("AI-Powered Resume Shortlisting")
    st.divider()

    st.markdown("**🔧 Configuration**")
    st.caption(f"Model: `{config.LLM_MODEL}`")
    st.caption(f"Shortlist threshold: ≥ {config.SHORTLIST_THRESHOLD}/10")

    st.divider()
    st.markdown("**📋 Rubric Weights**")
    for dim, weight in config.RUBRIC_WEIGHTS.items():
        dim_label = dim.replace("_", " ").title()
        st.caption(f"{dim_label}: **{int(weight*100)}%**")

    st.divider()
    st.markdown("**Security**")
    st.caption(" Prompt injection filtering")
    st.caption("PII masking in logs")
    st.caption("API keys via .env")
    st.caption("Pydantic output validation")
    st.caption("Human-in-the-loop overrides")


st.markdown('<h1 style="font-size:28px;font-weight:800;color:#1e1b4b">🎯 HR Resume Shortlisting Agent</h1>', unsafe_allow_html=True)
st.caption("Upload a Job Description and candidate resumes. The AI agent ranks candidates with a transparent rubric.")

tab_input, tab_results, tab_override, tab_audit = st.tabs([
    "📤 Input & Run", "📊 Results", "⚙️ HR Overrides", "📋 Audit Log"
])

with tab_input:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("#### 📄 Job Description")
        jd_input_mode = st.radio("JD Input Mode", ["Paste Text", "Upload File"], horizontal=True)

        jd_text = ""
        jd_file_path = ""

        if jd_input_mode == "Paste Text":
            jd_text = st.text_area(
                "Paste the full Job Description here",
                height=280,
                placeholder="We are hiring a Senior Backend Engineer...",
            )
        else:
            jd_file = st.file_uploader("Upload JD (PDF or TXT)", type=["pdf", "txt"])
            if jd_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(jd_file.name).suffix) as f:
                    f.write(jd_file.read())
                    jd_file_path = f.name
                st.success(f" JD uploaded: {jd_file.name}")

    with col2:
        st.markdown("#### 📂 Candidate Resumes")
        uploaded_files = st.file_uploader(
            "Upload Resume Files (PDF or DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=True,
        )

        if uploaded_files:
            st.success(f" {len(uploaded_files)} resume(s) uploaded")
            for f in uploaded_files:
                size_kb = len(f.getvalue()) / 1024
                st.caption(f"  • {f.name} ({size_kb:.0f} KB)")

    st.divider()

    can_run = (bool(jd_text.strip()) or bool(jd_file_path)) and bool(uploaded_files)
    run_col, _ = st.columns([1, 3])
    with run_col:
        run_btn = st.button(
            "🚀 Run Agent",
            disabled=not can_run,
            type="primary",
            use_container_width=True,
        )

    if not can_run:
        st.info("Provide a Job Description and at least one resume file to run the agent.")

    if run_btn and can_run:
        temp_dir = tempfile.mkdtemp()
        resume_paths = []
        for uploaded in uploaded_files:
            temp_path = Path(temp_dir) / uploaded.name
            temp_path.write_bytes(uploaded.getvalue())
            resume_paths.append(str(temp_path))

        progress_bar = st.progress(0, text="🔄 Starting pipeline...")

        progress_bar.progress(10, text="📋 Parsing Job Description...")

        with st.spinner("🤖 Agent running... This may take 1-2 minutes depending on resume count."):
            try:
                state = run_pipeline(
                    resume_paths=resume_paths,
                    jd_text=jd_text,
                    jd_file_path=jd_file_path,
                )
                st.session_state["pipeline_state"] = state
                progress_bar.progress(100, text="✅ Complete!")

                if state.get("errors"):
                    st.error(f"Pipeline errors: {state['errors']}")
                else:
                    st.success(
                        f"✅ Pipeline complete! "
                        f"{state['report'].total_candidates} candidates scored. "
                        f"Switch to the **Results** tab."
                    )
                    if state.get("warnings"):
                        for w in state["warnings"]:
                            st.warning(w)
            except Exception as e:
                st.error(f"Pipeline error: {str(e)}")
                progress_bar.empty()


with tab_results:
    state = st.session_state.get("pipeline_state")
    if not state or not state.get("report"):
        st.info("Run the agent first (Input & Run tab).")
    else:
        report = state["report"]
        jd_reqs = state.get("job_requirements")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Candidates", report.total_candidates)
        hire_count = sum(1 for s in report.scores if s.effective_recommendation() == "HIRE")
        maybe_count = sum(1 for s in report.scores if s.effective_recommendation() == "MAYBE")
        no_count = sum(1 for s in report.scores if s.effective_recommendation() == "NO_HIRE")
        m2.metric("✅ HIRE", hire_count)
        m3.metric("🟡 MAYBE", maybe_count)
        m4.metric("❌ NO_HIRE", no_count)

        if jd_reqs:
            with st.expander("📋 Parsed Job Requirements"):
                c1, c2 = st.columns(2)
                c1.write(f"**Domain:** {jd_reqs.domain}")
                c1.write(f"**Seniority:** {jd_reqs.seniority_level}")
                c1.write(f"**Min Experience:** {jd_reqs.min_years_experience or 'N/A'} years")
                c2.write(f"**Required Skills:** {', '.join(jd_reqs.required_skills[:10])}")
                c2.write(f"**Required Education:** {jd_reqs.required_education or 'N/A'}")

        st.divider()

        st.markdown('<p class="section-header">📊 Ranked Candidates</p>', unsafe_allow_html=True)

        for rank, score in enumerate(report.scores, 1):
            eff_total = score.effective_total()
            eff_rec = score.effective_recommendation()
            badge_cls = "hire-badge" if eff_rec == "HIRE" else "maybe-badge" if eff_rec == "MAYBE" else "no-badge"

            with st.expander(
                f"#{rank}  {score.full_name}  |  {eff_total:.2f}/10  |  {eff_rec}"
                + (" ⚙️ (overridden)" if score.hr_override else ""),
                expanded=(rank <= 2)
            ):
                col_a, col_b = st.columns([2, 1])

                with col_a:
                    st.write(score.summary_justification or "No summary available.")

                    dims_data = {
                        "Dimension": ["Skills Match (30%)", "Experience Relevance (25%)",
                                      "Education & Certs (15%)", "Project/Portfolio (20%)",
                                      "Communication Quality (10%)"],
                        "Score": [
                            score.skills_match.score,
                            score.experience_relevance.score,
                            score.education_certs.score,
                            score.project_portfolio.score,
                            score.communication_quality.score,
                        ],
                        "Justification": [
                            score.skills_match.justification,
                            score.experience_relevance.justification,
                            score.education_certs.justification,
                            score.project_portfolio.justification,
                            score.communication_quality.justification,
                        ]
                    }
                    df = pd.DataFrame(dims_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                with col_b:
                    st.markdown(f'<div class="{badge_cls}">{eff_rec}</div>', unsafe_allow_html=True)
                    st.metric("Weighted Total", f"{eff_total:.2f}/10")

                    if score.skill_matches:
                        st.markdown("**✅ Skill Matches:**")
                        st.caption(", ".join(score.skill_matches[:8]))
                    if score.skill_gaps:
                        st.markdown("**❌ Skill Gaps:**")
                        st.caption(", ".join(score.skill_gaps[:8]))

                    if score.hr_override:
                        st.warning(
                            f"⚙️ **HR Override** by {score.hr_override.overridden_by}\n\n"
                            f"Score: {score.hr_override.original_total} → {score.hr_override.overridden_total}\n\n"
                            f"Reason: {score.hr_override.reason}"
                        )

        st.divider()
        st.markdown("#### 📥 Download Report")
        dl_col1, dl_col2, dl_col3 = st.columns(3)

        output_paths = state.get("output_paths", {})
        if "json" in output_paths:
            with open(output_paths["json"], "rb") as f:
                dl_col1.download_button("📄 Download JSON", f.read(),
                                         file_name="shortlist_report.json", mime="application/json")
        if "html" in output_paths:
            with open(output_paths["html"], "rb") as f:
                dl_col2.download_button("🌐 Download HTML", f.read(),
                                         file_name="shortlist_report.html", mime="text/html")
        if "pdf" in output_paths:
            with open(output_paths["pdf"], "rb") as f:
                dl_col3.download_button("📕 Download PDF", f.read(),
                                         file_name="shortlist_report.pdf", mime="application/pdf")


with tab_override:
    state = st.session_state.get("pipeline_state")
    if not state or not state.get("candidate_scores"):
        st.info("Run the agent first to apply overrides.")
    else:
        st.markdown("#### ⚙️ Human-in-the-Loop Score Override")
        st.caption(
            "HR users can override any candidate's score. "
            "All overrides are logged with mandatory justification for compliance."
        )

        scores = state["candidate_scores"]
        candidate_names = {s.candidate_id: s.full_name for s in scores}

        with st.form("override_form"):
            selected_id = st.selectbox(
                "Select Candidate",
                options=list(candidate_names.keys()),
                format_func=lambda x: f"{candidate_names[x]} ({x})"
            )
            target = next((s for s in scores if s.candidate_id == selected_id), None)
            if target:
                st.info(f"Current score: **{target.weighted_total:.2f}/10** | Recommendation: **{target.recommendation}**")

            new_score = st.slider("New Total Score", 0.0, 10.0, value=float(target.weighted_total) if target else 5.0, step=0.5)
            new_rec = st.selectbox("New Recommendation", ["HIRE", "MAYBE", "NO_HIRE"])
            hr_user = st.text_input("Your HR User ID", value="hr_manager_01")
            reason = st.text_area(
                "Override Reason (Mandatory — minimum 10 characters)",
                placeholder="e.g. Candidate has been personally interviewed and showed strong leadership skills not reflected in resume."
            )

            submit = st.form_submit_button("Apply Override", type="primary")

        if submit:
            if not reason or len(reason.strip()) < 10:
                st.error("Override reason is mandatory and must be at least 10 characters.")
            elif not hr_user.strip():
                st.error("HR User ID is required.")
            else:
                try:
                    apply_hr_override(
                        score=target,
                        hr_user=hr_user,
                        new_total=new_score,
                        new_recommendation=new_rec,
                        reason=reason,
                    )
                    st.success(f"✅ Override applied! {target.full_name}: {target.weighted_total:.2f} → {new_score:.2f} ({new_rec})")
                    st.info("Switch to Results tab to see updated ranking.")
                except ValueError as e:
                    st.error(str(e))


with tab_audit:
    st.markdown("#### 📋 HR Override Audit Log")
    st.caption("All HR overrides are logged for compliance. This log cannot be deleted.")

    log = get_override_log()
    if not log:
        st.info("No overrides recorded yet.")
    else:
        df = pd.DataFrame(log)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total overrides: {len(log)}")
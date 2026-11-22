from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from database import (
    init_db, create_user, authenticate_user, save_resume,
    list_resumes, get_resume, delete_resume
)
from resume_utils import (
    make_summary, improve_bullet, skill_gap,
    render_resume_html
)
from ai_helper import ask as generate_ai_text
from ats_engine import ats_match, use_built_resume
import ai_helper
from ai_coach import render_ai_coach
from pdf_utils import create_resume_pdf
from resume_wizard import render_resume_wizard, edit_saved
from extra_pages import (
    init_extra_tables, load_css, count_applications, render_cover_letter,
    render_job_tracker, render_interview_prep, render_dashboard, render_linkedin, render_checklist
)

st.set_page_config(page_title="CareerForge | AI Resume Studio", page_icon="🚀", layout="wide")
init_db()
init_extra_tables()
load_css(os.path.join(os.path.dirname(__file__), "style.css"))

# ---------------- Authentication ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown(
            '<div class="cf-brand">'
            '<div class="cf-logo">🚀 CareerForge</div>'
            '<div class="cf-headline">Turn your experience into interviews.</div>'
            '<p class="cf-lede">Build the resume, match it to the job, and track every application in one place.</p>'
            '<div class="cf-feat"><b>Resume builder</b>Three templates with one-click PDF download</div>'
            '<div class="cf-feat"><b>ATS analyzer</b>See which job keywords your resume is missing</div>'
            '<div class="cf-feat"><b>Application toolkit</b>Cover letters, interview prep and a job tracker</div>'
            '<p class="cf-note">Your data stays in a local SQLite database on your computer.</p>'
            '</div>', unsafe_allow_html=True)
    right.markdown('<div class="cf-welcome">Welcome back</div>'
                   '<div class="cf-welcome-sub">Log in, or create an account to get started.</div>',
                   unsafe_allow_html=True)
    tab_login, tab_register = right.tabs(["Login", "Create account"])
    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("Email", placeholder="you@example.com")
            login_password = st.text_input("Password", type="password", placeholder="Your password")
            login_submit = st.form_submit_button("Login", use_container_width=True)
        if login_submit:
            found = authenticate_user(login_email, login_password)
            if found:
                st.session_state.user = found
                st.rerun()
            else:
                st.error("Email or password is incorrect.")
    with tab_register:
        with st.form("register_form"):
            reg_name = st.text_input("Your name")
            reg_email = st.text_input("Email address")
            reg_password = st.text_input("Password (at least 8 characters)", type="password")
            reg_confirm = st.text_input("Confirm password", type="password")
            reg_submit = st.form_submit_button("Create account", use_container_width=True)
        if reg_submit:
            if not reg_name.strip() or not reg_email.strip():
                st.error("Enter your name and email.")
            elif len(reg_password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = create_user(reg_name, reg_email, reg_password)
                if ok:
                    st.success(message + " You can now log in.")
                else:
                    st.error(message)
    st.stop()

user = st.session_state.user
uid = str(user["id"])

st.sidebar.title("🚀 CareerForge")
st.sidebar.caption(f"Signed in as {user['name']}")
st.sidebar.caption("AI: " + (ai_helper.status() or "not connected"))
page = st.sidebar.radio("Workspace", [
    "Dashboard", "AI Resume Coach", "Resume Builder", "ATS Analyzer",
    "AI Writing Assistant", "Skill Gap Planner", "My Resumes",
    "Cover Letter", "Job Tracker", "Interview Prep",
    "LinkedIn Optimizer", "Resume Checklist",
], key="page")
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.rerun()
st.sidebar.divider()
st.sidebar.caption("Local prototype • SQLite")

if page == "Dashboard":
    render_dashboard(user, len(list_resumes(user["id"])))

elif page == "Resume Builder":
    render_resume_wizard(user, create_resume_pdf, save_resume)

elif page == "ATS Analyzer":
    st.title("ATS Analyzer")
    st.caption("Compare your resume with a job description.")
    st.button("Use my resume from Resume Builder", on_click=use_built_resume)
    resume_text = st.text_area("Paste your resume text", height=230, key="ats_resume")
    job_text = st.text_area("Paste the target job description", height=230)
    if st.button("Analyze match", type="primary"):
        if not resume_text.strip() or not job_text.strip():
            st.warning("Paste both your resume and the job description.")
        else:
            result = ats_match(resume_text, job_text)
            st.metric("Keyword coverage estimate", f"{result['score']}%")
            st.progress(result["score"] / 100)
            a, b = st.columns(2)
            with a:
                st.markdown("**Keywords found**")
                st.markdown("".join(f'<span class="cf-tag">{k}</span>' for k in result["matched"]) or "None detected",
                            unsafe_allow_html=True)
            with b:
                st.markdown("**Missing skills (most important)**")
                st.markdown("".join(f'<span class="cf-tag">{k}</span>' for k in result["missing_skills"]) or "None - every skill in the job is covered",
                            unsafe_allow_html=True)
                if result["other_missing"]:
                    st.markdown("**Other missing keywords**")
                    st.markdown("".join(f'<span class="cf-tag">{k}</span>' for k in result["other_missing"]), unsafe_allow_html=True)
            st.markdown("**Suggestions**")
            for suggestion in result["suggestions"]:
                st.write("• " + suggestion)
            st.caption("This is a transparent keyword-coverage estimate, not a real vendor ATS score. It does not judge truthfulness, seniority, formatting or semantic relevance.")

elif page == "AI Writing Assistant":
    st.title("AI Writing Assistant")
    mode = st.selectbox("Choose a tool", ["Professional summary", "Improve a bullet point", "Tailor a summary to a job"])
    if mode == "Professional summary":
        candidate = st.text_input("Name")
        target = st.text_input("Target role")
        candidate_skills = st.text_area("Skills")
        education_text = st.text_area("Education")
        context = f"Name: {candidate}\nRole: {target}\nSkills: {candidate_skills}\nEducation: {education_text}"
        task = "Write a concise, truthful 3-sentence resume summary using only the supplied facts. Do not invent achievements."
        fallback = make_summary(candidate or "Candidate", target, candidate_skills, education_text)
    elif mode == "Improve a bullet point":
        bullet = st.text_area("Your original bullet", placeholder="Built a website using HTML and CSS")
        context = bullet
        task = "Rewrite this resume bullet to be clear, specific and professional. Do not invent metrics or responsibilities."
        fallback = improve_bullet(bullet)
    else:
        summary_input = st.text_area("Current summary")
        job_input = st.text_area("Target job description")
        context = f"Current summary:\n{summary_input}\n\nJob description:\n{job_input}"
        task = "Tailor the summary to the job description using only facts in the current summary. Do not add skills or experience not stated."
        fallback = "Review the current summary and job description. Add only relevant skills and experience that are genuinely yours."
    if st.button("Generate suggestion", type="primary"):
        if not context.strip():
            st.warning("Enter the requested information first.")
        else:
            result, used_ai = generate_ai_text(task, context, fallback)
            st.text_area("Editable suggestion", result, height=180)
            if used_ai:
                st.success("Generated with the configured AI provider.")
            else:
                st.info("Showing the built-in fallback. Configure OPENAI_API_KEY to enable API-generated text.")

elif page == "Skill Gap Planner":
    st.title("Skill Gap Planner")
    st.caption("Role-based learning planner.")
    target_role = st.selectbox("Target role", [
        "Python Developer", "Web Developer", "Data Analyst",
        "Data Scientist", "AI / ML Engineer"
    ])
    current_skills = st.text_input("Skills you already have (comma-separated)")
    if st.button("Build my learning gap list", type="primary"):
        present, suggested = skill_gap(target_role, current_skills)
        st.markdown("**Already listed**")
        st.write(", ".join(present) or "No matching skills entered.")
        st.markdown("**Suggested skills to explore**")
        st.write(", ".join(suggested) or "No suggestions.")
        st.caption("Suggestions are a starter checklist. Compare them with real job postings and your current level.")

elif page == "My Resumes":
    st.title("My Resumes")
    rows = list_resumes(user["id"])
    if not rows:
        st.info("No saved resumes yet. Create one in Resume Builder.")
    for row in rows:
        rid, name, email, created = row
        with st.expander(f"#{rid} · {name} · {created}"):
            saved = get_resume(user["id"], rid)
            if saved:
                st.write(saved)
                st.download_button("Download PDF", create_resume_pdf(saved), f"resume_{rid}.pdf", "application/pdf", key=f"pdf_{rid}")
                st.button("Edit in Resume Builder", key=f"edit_saved_{rid}", on_click=edit_saved, args=(saved, rid, user["id"]))
            if st.button("Delete resume", key=f"delete_{rid}"):
                delete_resume(user["id"], rid)
                st.rerun()

# ---------------- New pages ----------------
elif page == "Cover Letter":
    render_cover_letter(user["name"])
elif page == "Job Tracker":
    render_job_tracker(uid)
elif page == "Interview Prep":
    render_interview_prep()
elif page == "LinkedIn Optimizer":
    render_linkedin()
elif page == "Resume Checklist":
    render_checklist()
elif page == "AI Resume Coach":
    render_ai_coach()

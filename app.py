from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from database import (
    init_db, create_user, authenticate_user, save_resume,
    list_resumes, get_resume, delete_resume
)
from resume_utils import (
    ats_match, make_summary, improve_bullet, skill_gap,
    render_resume_html, generate_ai_text
)
from pdf_utils import create_resume_pdf

st.set_page_config(page_title="CareerForge | AI Resume Studio", page_icon="🚀", layout="wide")
init_db()

st.markdown("""
<style>
.stApp {background:linear-gradient(145deg,#0b1020,#121b30);color:#eef2ff}
[data-testid="stSidebar"] {background:#111a2b}
.block-container {max-width:1250px;padding-top:2rem}
h1,h2,h3 {color:#a8c7ff}
div[data-testid="stMetric"] {background:#18243a;padding:15px;border:1px solid #263b5d;border-radius:14px}
.stButton>button,.stDownloadButton>button {border-radius:9px;font-weight:650}
div[data-testid="stForm"] {border:1px solid #2a3c59;border-radius:14px;padding:18px}
</style>
""", unsafe_allow_html=True)

# ---------------- Authentication ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🚀 CareerForge")
    st.caption("AI Career & Resume Studio")
    tab_login, tab_register = st.tabs(["Login", "Create account"])
    with tab_login:
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login", use_container_width=True)
        if login_submit:
            user = authenticate_user(login_email, login_password)
            if user:
                st.session_state.user = user
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
st.sidebar.title("🚀 CareerForge")
st.sidebar.caption(f"Signed in as {user['name']}")
page = st.sidebar.radio("WORKSPACE", [
    "Dashboard", "Resume Builder", "ATS Analyzer",
    "AI Writing Assistant", "Skill Gap Planner", "My Resumes"
])
if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.user = None
    st.rerun()
st.sidebar.divider()
st.sidebar.caption("Local prototype • SQLite")

st.title("CareerForge — AI Career & Resume Studio")
st.caption("Build a resume, tailor it to a job, and plan your next skills.")
st.divider()

if page == "Dashboard":
    resumes = list_resumes(user["id"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Your saved resumes", len(resumes))
    c2.metric("Resume templates", "3")
    c3.metric("Career tools", "3")
    st.subheader(f"Welcome, {user['name']} 👋")
    st.write("Start with Resume Builder, then use ATS Analyzer to compare your resume with a job description.")
    st.info("AI provider is optional. Add an OpenAI API key in your local `.env` file to enable generated writing. Without it, built-in rule-based helpers still work.")
    st.markdown("**Suggested workflow**")
    st.write("1. Create your resume.  2. Download or save it.  3. Paste a target job description into ATS Analyzer.  4. Improve only the gaps that accurately reflect your experience.")

elif page == "Resume Builder":
    st.subheader("Create / update your resume")
    with st.form("resume_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            location = st.text_input("City / location")
            role = st.text_input("Target job title", placeholder="e.g. Junior Python Developer")
        with c2:
            template = st.selectbox("Design template", ["Modern", "Simple", "Creative"])
            education = st.text_area("Education", placeholder="Course, institute, year, relevant coursework...")
            skills = st.text_area("Skills", placeholder="Python, HTML, CSS, SQL...")
        summary = st.text_area("Professional summary", height=100)
        projects = st.text_area("Projects", height=120, placeholder="Project name, what you built, tools used, measurable result...")
        experience = st.text_area("Experience / internship", height=100)
        certifications = st.text_area("Certifications / achievements", height=80)
        languages = st.text_input("Languages")
        submitted = st.form_submit_button("Generate resume preview", use_container_width=True)
    if submitted:
        if not name.strip() or not email.strip():
            st.error("Full name and email are required.")
        else:
            if not summary.strip():
                summary = make_summary(name, role, skills, education)
            st.session_state.resume_draft = {
                "name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                "location": location.strip(), "role": role.strip(), "template": template,
                "education": education.strip(), "skills": skills.strip(), "summary": summary.strip(),
                "projects": projects.strip(), "experience": experience.strip(),
                "certifications": certifications.strip(), "languages": languages.strip()
            }
    data = st.session_state.get("resume_draft")
    if data:
        st.subheader("Preview")
        st.components.v1.html(render_resume_html(data), height=850, scrolling=True)
        st.download_button("⬇️ Download PDF", create_resume_pdf(data), "careerforge_resume.pdf", "application/pdf", use_container_width=True)
        if st.button("💾 Save to my account", use_container_width=True):
            rid = save_resume(user["id"], data)
            st.success(f"Resume saved to your account (ID {rid}).")

elif page == "ATS Analyzer":
    st.subheader("ATS / job-description match analyzer")
    resume_text = st.text_area("Paste your resume text", height=230)
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
                st.write(", ".join(result["matched"]) or "None detected")
            with b:
                st.markdown("**Potential missing keywords**")
                st.write(", ".join(result["missing"]) or "No missing keywords detected")
            st.markdown("**Suggestions**")
            for suggestion in result["suggestions"]:
                st.write("• " + suggestion)
            st.caption("This is a transparent keyword-coverage estimate, not a real vendor ATS score. It does not judge truthfulness, seniority, formatting or semantic relevance.")

elif page == "AI Writing Assistant":
    st.subheader("AI writing assistant")
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
    st.subheader("Role-based learning planner")
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
    st.subheader("Your saved resumes")
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
            if st.button("Delete resume", key=f"delete_{rid}"):
                delete_resume(user["id"], rid)
                st.success("Deleted. Refresh this page to update the list.")

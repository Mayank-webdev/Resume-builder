"""Extra CareerForge pages: drop this file next to your app.py."""
import os
import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_PATH = "careerforge.db"  # <- change to the SQLite file your app already uses
STATUSES = ["Wishlist", "Applied", "Interview", "Offer", "Rejected"]


# ---------- helpers ----------
def _conn():
    return sqlite3.connect(DB_PATH)


def init_extra_tables():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS job_applications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT NOT NULL, company TEXT NOT NULL, role TEXT NOT NULL,
                status TEXT DEFAULT 'Wishlist', applied_on TEXT, notes TEXT)"""
        )


def count_applications(user):
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM job_applications WHERE user=?", (user,)).fetchone()[0]


def load_css(path="style.css"):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def ai_generate(prompt):
    """Returns generated text, or None when no OpenAI key is set (rule-based fallback is used)."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI

        r = OpenAI(api_key=key).chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
        )
        return r.choices[0].message.content
    except Exception as e:  # network, quota, bad key...
        st.warning(f"AI request failed, using the built-in template instead. ({e})")
        return None


def _split(text):
    return [s.strip() for s in text.split(",") if s.strip()]


# ---------- 1. Cover letter ----------
def render_cover_letter(user=""):
    st.title("Cover Letter Generator")
    st.caption("Write a letter that matches the job. Only include what is true for you.")
    with st.form("cover_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Your name", value=user)
        company = c2.text_input("Company")
        role = c1.text_input("Role you are applying for")
        tone = c2.selectbox("Tone", ["Professional", "Friendly", "Confident"])
        skills = st.text_input("Your top skills (comma separated)", "Python, SQL, Streamlit")
        win = st.text_area("One achievement you are proud of", height=90)
        go = st.form_submit_button("Generate letter")

    if go:
        if not (name and company and role):
            st.error("Add your name, the company and the role first.")
            return
        sk = _split(skills)
        text = ai_generate(
            f"Write a {tone.lower()} 250-word cover letter for {name} applying to {company} "
            f"as {role}. Skills: {', '.join(sk)}. Achievement: {win}. Do not invent facts."
        )
        if not text:
            opener = {"Professional": "I am writing to apply for", "Friendly": "I'm excited to apply for",
                      "Confident": "I am the right fit for"}[tone]
            text = (
                f"Dear Hiring Team at {company},\n\n{opener} the {role} position. "
                f"My background in {', '.join(sk[:-1]) + ' and ' + sk[-1] if len(sk) > 1 else ''.join(sk)} "
                f"has prepared me to contribute from day one.\n\n"
                + (f"{win.strip()}\n\n" if win.strip() else "")
                + f"I would welcome the chance to discuss how I can help {company} reach its goals.\n\n"
                f"Sincerely,\n{name}"
            )
        st.markdown(f'<div class="cf-letter">{text}</div>', unsafe_allow_html=True)
        st.download_button("Download as .txt", text, file_name=f"cover_letter_{company}.txt")


# ---------- 2. Job tracker ----------
def render_job_tracker(user):
    st.title("Job Tracker")
    st.caption("Keep every application and its status in one place.")
    with st.expander("Add an application", expanded=False):
        with st.form("job_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            company = c1.text_input("Company")
            role = c2.text_input("Role")
            status = c3.selectbox("Status", STATUSES)
            applied = st.date_input("Date applied", value=date.today())
            notes = st.text_area("Notes", height=70)
            if st.form_submit_button("Save application"):
                if company and role:
                    with _conn() as c:
                        c.execute(
                            "INSERT INTO job_applications(user,company,role,status,applied_on,notes) "
                            "VALUES(?,?,?,?,?,?)",
                            (user, company, role, status, str(applied), notes),
                        )
                    st.success("Application saved.")
                else:
                    st.error("Company and role are required.")

    with _conn() as c:
        df = pd.read_sql_query(
            "SELECT id, company, role, status, applied_on, notes FROM job_applications "
            "WHERE user=? ORDER BY id DESC", c, params=(user,))
    if df.empty:
        st.info("No applications yet. Add your first one above.")
        return

    cols = st.columns(len(STATUSES))
    for col, s in zip(cols, STATUSES):
        col.metric(s, int((df.status == s).sum()))
    st.dataframe(df.drop(columns="id"), use_container_width=True, hide_index=True)

    st.subheader("Update or remove")
    pick = st.selectbox("Application", df.id, format_func=lambda i: "{} - {}".format(
        df.loc[df.id == i, "company"].iloc[0], df.loc[df.id == i, "role"].iloc[0]))
    c1, c2 = st.columns(2)
    new_status = c1.selectbox("New status", STATUSES, key="ns")
    if c1.button("Update status"):
        with _conn() as c:
            c.execute("UPDATE job_applications SET status=? WHERE id=? AND user=?", (new_status, pick, user))
        st.rerun()
    if c2.button("Delete application"):
        with _conn() as c:
            c.execute("DELETE FROM job_applications WHERE id=? AND user=?", (pick, user))
        st.rerun()


# ---------- 3. Interview prep ----------
QUESTIONS = {
    "General": ["Tell me about yourself.", "Why do you want this role?",
                "Describe a challenge you solved.", "Where do you see yourself in 3 years?"],
    "Software / Data": ["Explain a project you built end to end.", "How do you debug a failing query or script?",
                        "What is the difference between a list and a tuple in Python?",
                        "How would you design a simple database schema for an app?"],
    "Behavioral (STAR)": ["Tell me about a time you disagreed with a teammate.",
                          "Describe a deadline you almost missed.", "Give an example of leading without authority."],
}


def render_interview_prep():
    st.title("Interview Prep")
    st.caption("Practice questions based on your role and skills.")
    cat = st.selectbox("Question set", list(QUESTIONS))
    skills = _split(st.text_input("Your skills (optional, comma separated)", "Python, SQL"))
    qs = QUESTIONS[cat] + [f"Tell me about a project where you used {s}." for s in skills]
    for i, q in enumerate(qs):
        with st.expander(q):
            st.text_area("Draft your answer", key=f"ans_{cat}_{i}", height=100)
    with st.expander("How to answer with STAR"):
        st.markdown("**Situation** - the context. **Task** - your responsibility. "
                    "**Action** - what you did. **Result** - the measurable outcome.")


# ---------- 4. LinkedIn optimizer ----------
def render_linkedin():
    st.title("LinkedIn Optimizer")
    st.caption("Headline and About-section drafts from your real experience.")
    role = st.text_input("Target role", "Python Developer")
    skills = _split(st.text_input("Key skills", "Python, SQL, Streamlit"))
    years = st.text_input("Experience (e.g. fresher, 2 years)", "fresher")
    if st.button("Generate drafts") and role:
        top = " | ".join(skills[:3])
        st.subheader("Headline options")
        for h in (f"{role} | {top}", f"{role} building with {', '.join(skills[:2])}",
                  f"Aspiring {role} | {top} | Open to work"):
            st.code(h, language=None)
        about = ai_generate(f"Write a 90-word LinkedIn About section for a {role} ({years}) "
                            f"skilled in {', '.join(skills)}. Do not invent facts.") or (
            f"I am a {role} ({years}) who enjoys turning ideas into working software. "
            f"I work with {', '.join(skills)} and I am looking for a team where I can learn fast and ship useful work.")
        st.subheader("About section")
        st.write(about)


# ---------- 5. Resume checklist ----------
CHECKS = [
    "Contact details and a professional email are at the top",
    "One page for under 8 years of experience",
    "Every bullet starts with an action verb",
    "At least half of the bullets contain a number or result",
    "Skills match the keywords in the job description",
    "No spelling or grammar mistakes",
    "Links to GitHub / portfolio / LinkedIn work",
    "Saved as PDF with a clear file name",
]


def render_checklist():
    st.title("Resume Checklist")
    st.caption("Run through this before every application.")
    done = sum(st.checkbox(c, key=f"chk_{i}") for i, c in enumerate(CHECKS))
    st.progress(done / len(CHECKS), text=f"{done} of {len(CHECKS)} complete")
    if done == len(CHECKS):
        st.success("Ready to send.")


# ---------- Dashboard ----------
TIPS = [
    "Tailor your resume to each job: mirror the keywords the posting uses, but only for skills you really have.",
    "Start every bullet with an action verb and add a number or result where you can.",
    "Follow up 5-7 days after applying. A short, polite message keeps you on the recruiter's radar.",
    "Keep your resume to one page until you have 8+ years of experience.",
    "Prepare 3 STAR stories (Situation, Task, Action, Result). They cover most behavioral questions.",
    "Your LinkedIn headline should say what you do, not just 'Student' or 'Job seeker'.",
    "Put your strongest project first. Recruiters often read only the top third of a resume.",
]


def go_to(page):
    """Button callback: jump to a sidebar page."""
    st.session_state.page = page


def render_dashboard(user, n_resumes):
    from datetime import datetime, timedelta

    uid = str(user["id"])
    with _conn() as c:
        df = pd.read_sql_query(
            "SELECT company, role, status, applied_on FROM job_applications "
            "WHERE user=? ORDER BY id DESC", c, params=(uid,))
    hour = datetime.now().hour
    greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    first = user["name"].split()[0]
    total = len(df)
    interviews = int((df.status == "Interview").sum()) if total else 0
    offers = int((df.status == "Offer").sum()) if total else 0

    if n_resumes == 0:
        line = "Your search starts with a resume. Build your first one in a few minutes."
    elif total == 0:
        line = "Your resume is ready. Time to track your first application."
    else:
        line = f"You are tracking {total} application{'s' if total != 1 else ''}, with {interviews} at interview stage."
    st.markdown(f'<div class="cf-hero"><h2>{greet}, {first}</h2><p>{line}</p></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Saved resumes", n_resumes)
    c2.metric("Applications", total)
    c3.metric("Interviews", interviews)
    c4.metric("Offers", offers)

    st.subheader("Quick actions")
    q = st.columns(4)
    for col, (label, page) in zip(q, [("Build a resume", "Resume Builder"), ("Check ATS match", "ATS Analyzer"),
                                      ("Write a cover letter", "Cover Letter"), ("Track a job", "Job Tracker")]):
        col.button(label, key=f"qa_{page}", on_click=go_to, args=(page,), use_container_width=True)

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Application pipeline")
        if total:
            counts = df.status.value_counts().reindex(STATUSES).fillna(0)
            st.bar_chart(counts, color="#f2a33a", height=220)
            st.caption("Most recent applications")
            st.dataframe(df.head(5), use_container_width=True, hide_index=True)
        else:
            st.info("Nothing here yet. Add an application in Job Tracker and your pipeline appears here.")
    with right:
        st.subheader("This week")
        goal = st.number_input("Weekly application goal", 1, 50, 5)
        week = 0
        if total:
            dates = pd.to_datetime(df.applied_on, errors="coerce")
            week = int((dates >= pd.Timestamp.now() - timedelta(days=7)).sum())
        st.progress(min(week / goal, 1.0), text=f"{week} of {goal} applications sent in the last 7 days")

        st.subheader("Getting started")
        for done, text in [(n_resumes > 0, "Save your first resume"),
                           (total > 0, "Track an application"),
                           (offers > 0 or interviews > 0, "Reach the interview stage")]:
            st.markdown(f'<div class="cf-step {"done" if done else ""}">{"✓" if done else "○"} &nbsp;{text}</div>',
                        unsafe_allow_html=True)

    st.markdown(f'<div class="cf-card"><b>Tip of the day</b><br>{TIPS[date.today().toordinal() % len(TIPS)]}</div>',
                unsafe_allow_html=True)

"""Better ATS keyword matcher: recognises real skills (and their variants) and ignores filler words."""
import re
from collections import Counter


def _norm(text):
    return " " + re.sub(r"[^a-z0-9+#]+", " ", (text or "").lower()).strip() + " "


# "Display name | variant | variant" - a skill counts as found if the name or any variant appears.
SKILLS = """Python
Java
JavaScript | js
TypeScript
C++
C#
SQL | structured query language
MySQL
PostgreSQL | postgres
MongoDB
HTML
CSS
React | reactjs
Node.js | nodejs
Django
Flask
Streamlit
FastAPI
Git | github
REST APIs | rest api | restful
Docker
AWS | amazon web services
Azure
Google Cloud | gcp
Linux
Excel | ms excel | microsoft excel | spreadsheets
Power BI | powerbi
Tableau
Statistics | statistical | statistical analysis
Data Visualization | visualization | visualisation | data viz | dashboards | dashboard
Data Cleaning | cleaning | clean and | clean data | cleaning data | cleaned data | data cleansing | data preparation | data wrangling
Data Analysis | data analyst | data analytics | analyze data | analyzing data | analysing data
Machine Learning | ml
Deep Learning
NLP | natural language processing
Pandas
NumPy
Scikit-learn | sklearn
TensorFlow
PyTorch
Communication | communicate | communicating
Teamwork | team work | collaboration | collaborate | collaborative
Leadership
Problem Solving | problem-solving
Time Management
Project Management
Agile | scrum
Testing | unit testing
Debugging
Figma
Customer Service
Sales
Accounting
Reporting | reports | report"""

VOCAB = []  # (display, [normalised variants])
for line in SKILLS.splitlines():
    names = [n.strip() for n in line.split("|")]
    VOCAB.append((names[0], [_norm(n) for n in names]))

FILLER = set("""able about above across after also among and any are been being both but can could does each etc for from
have having help helps join looking make makes more most must need needs other our over per plus such than that the their
them then there these they this those through under use used using want well what when where which while who will with within
without work working would you your good better strong great ability related relevant including include preferred required
requirements requirement responsibilities responsibility role position candidate candidates company team teams teammate
teammates junior senior experience experienced years year knowledge understanding clearly find write present prepare power
build make decisions business join looking field degree bachelor master""".split())


def _stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def _has(text, variants):
    return any(v in text for v in variants)


def ats_match(resume_text, job_text):
    r, j = _norm(resume_text), _norm(job_text)
    found, missing = [], []
    for display, variants in VOCAB:
        if _has(j, variants):
            (found if _has(r, variants) else missing).append(display)

    r_stems = {_stem(w) for w in r.split()}
    skill_words = {w for _, vs in VOCAB for v in vs for w in v.split()}
    counts, surface = Counter(), {}
    for w in j.split():
        if len(w) >= 4 and w not in FILLER and w not in skill_words and not w.isdigit():
            counts[_stem(w)] += 1
            surface.setdefault(_stem(w), w)
    other = [s for s, c in counts.most_common() if c >= 2][:15]
    other_found = [surface[s] for s in other if s in r_stems]
    other_missing = [surface[s] for s in other if s not in r_stems]

    total = 3 * (len(found) + len(missing)) + len(other)
    score = round(100 * (3 * len(found) + len(other_found)) / total) if total else 0

    tips = []
    if missing:
        tips.append("Add these skills to your Skills section ONLY if they are true for you: " + ", ".join(missing[:6]) + ".")
        tips.append("For skills you really have, show them in a project or job bullet with a result, not just in a list.")
    if not found and not missing:
        tips.append("No standard skills were detected in the job description. Paste the full text, including requirements.")
    if score < 40 and missing:
        tips.append("Coverage is low. If the role matters to you, build a small project that uses the missing skills.")
    elif score >= 70:
        tips.append("Strong coverage. Now make sure each point is backed by a real example.")
    tips.append("Tailor your summary and project descriptions to the role, without copying the job description.")
    return {"score": score, "matched": found + other_found, "missing": missing + other_missing,
            "missing_skills": missing, "other_missing": other_missing, "suggestions": tips}


def use_built_resume():
    """Button callback: fill the ATS text box with the resume made in Resume Builder."""
    import streamlit as st
    from resume_wizard import _D, _data
    d = _data(_D())
    st.session_state["ats_resume"] = "\n".join(v for k, v in d.items() if v and k != "template")

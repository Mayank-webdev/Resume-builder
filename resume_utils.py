import os, re
from html import escape

STOPWORDS = {
    "the","and","for","with","you","your","are","was","were","this","that",
    "have","has","from","will","our","their","job","work","role","skills",
    "ability","experience","required","must","should","can","who","what",
    "when","to","of","in","a","an","is","as","by","on","or","be"
}
ROLE_SKILLS = {
    "python developer": ["Python","Git","SQL","Object-oriented programming","Testing","Flask or Django","REST APIs"],
    "web developer": ["HTML","CSS","JavaScript","Responsive design","Git","React","Accessibility"],
    "data analyst": ["Excel","SQL","Python","Pandas","Data visualization","Statistics","Power BI or Tableau"],
    "data scientist": ["Python","Statistics","Pandas","NumPy","Machine learning","SQL","Data visualization"],
    "ai / ml engineer": ["Python","Linear algebra","Statistics","Scikit-learn","PyTorch or TensorFlow","Model evaluation","Git"]
}

def keywords(text):
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.]*", text.lower())
    return {w for w in tokens if len(w) > 2 and w not in STOPWORDS}

def ats_match(resume_text, job_text):
    job, resume = keywords(job_text), keywords(resume_text)
    if not job:
        return {"score": 0, "matched": [], "missing": [], "suggestions": ["The job description did not contain enough keywords to compare."]}
    matched, missing = sorted(job & resume), sorted(job - resume)
    score = round(100 * len(matched) / len(job))
    suggestions = []
    if missing:
        suggestions.append("Review the missing terms and add only those that accurately describe your skills or experience.")
    if score < 40:
        suggestions.append("Tailor your resume summary and project descriptions to the role, without copying the job description.")
    elif score < 70:
        suggestions.append("Improve evidence for relevant skills by describing where and how you used them.")
    else:
        suggestions.append("Check that each matched keyword is supported by a concrete example in your resume.")
    return {"score": score, "matched": matched, "missing": missing, "suggestions": suggestions}

def make_summary(name, role, skills, education):
    skill_list = [x.strip() for x in skills.split(",") if x.strip()]
    skill_text = ", ".join(skill_list[:7]) if skill_list else "problem-solving and communication"
    edu = education.strip() or "an academic background"
    job = role.strip() or "entry-level"
    return (f"{name.strip()} is an aspiring {job} professional with {edu}. "
            f"Key skills include {skill_text}. Interested in applying technical knowledge, "
            "learning continuously, and contributing to practical projects and collaborative teams.")

def improve_bullet(text):
    result = text.strip()
    replacements = [
        (r"^\s*made\b", "Developed"), (r"^\s*built\b", "Built"),
        (r"^\s*created\b", "Designed and developed"), (r"^\s*worked on\b", "Contributed to"),
        (r"^\s*helped\b", "Assisted with"), (r"^\s*used\b", "Used")
    ]
    for pattern, replacement in replacements:
        if re.search(pattern, result, flags=re.I):
            result = re.sub(pattern, replacement, result, count=1, flags=re.I)
            break
    return result[:1].upper() + result[1:] if result else ""

def skill_gap(role, current_skills):
    required = ROLE_SKILLS.get(role.lower(), [])
    current = {x.strip().lower() for x in current_skills.split(",") if x.strip()}
    return ([s for s in required if s.lower() in current],
            [s for s in required if s.lower() not in current])

def generate_ai_text(task, context, fallback):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback, False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=f"{task}\n\nUse only these facts:\n{context}"
        )
        text = response.output_text.strip()
        return (text or fallback), bool(text)
    except Exception:
        return fallback, False

def render_resume_html(data):
    accent, pale = {
        "Modern": ("#2563eb","#eff6ff"),
        "Simple": ("#252525","#f5f5f5"),
        "Creative": ("#7c3aed","#f5f3ff")
    }.get(data.get("template"), ("#2563eb","#eff6ff"))
    fields = [
        ("Professional Summary","summary"),("Education","education"),("Skills","skills"),
        ("Projects","projects"),("Experience","experience"),
        ("Certifications & Achievements","certifications"),("Languages","languages")
    ]
    sections = ""
    for title, key in fields:
        value = data.get(key, "")
        if value.strip():
            sections += f"<h3>{escape(title)}</h3><p>{escape(value).replace(chr(10),'<br>')}</p>"
    return f"""<div style="font-family:Arial,sans-serif;background:#fff;color:#222;padding:38px;max-width:850px;margin:auto;border-top:9px solid {accent};min-height:700px">
    <h1 style="color:{accent};margin-bottom:5px">{escape(data.get('name',''))}</h1>
    <p>{escape(data.get('email',''))} | {escape(data.get('phone',''))} | {escape(data.get('location',''))}</p>
    <p style="background:{pale};padding:9px">{escape(data.get('role',''))}</p>{sections}</div>"""

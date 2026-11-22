"""Resume Now-style flow: pick a template, then fill Header > Experience > Education > Skills > Summary > Extras > Finalize."""
import json
import re
from datetime import datetime
from html import escape as esc

import streamlit as st
import streamlit.components.v1 as components


def _show_html(html, height):
    """st.components.v1.html is deprecated; use st.iframe when this Streamlit version has it."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        components.html(html, height=height)

STEPS = ["Template", "Header", "Experience", "Education", "Skills", "Summary", "Extras", "Finalize"]
ACCENTS = {"Crimson": "#c8414b", "Navy": "#1f3a68", "Teal": "#17898c", "Forest": "#2f7d5b",
           "Amber": "#c97a12", "Violet": "#6a4fb3", "Slate": "#46546b", "Black": "#1a1a1a"}
# design id -> (label, template name your existing PDF code understands)
DESIGNS = {"banner": ("Banner", "Modern"), "classic": ("Classic", "Simple"),
           "sidebar": ("Sidebar", "Creative"), "minimal": ("Minimal", "Simple"),
           "photo": ("Photo", "Modern")}
SUGG = {
    "data": ["Excel", "SQL", "Python", "Power BI", "Tableau", "Statistics", "Data cleaning", "Dashboards"],
    "web": ["HTML", "CSS", "JavaScript", "React", "Responsive design", "Git", "REST APIs", "Figma"],
    "python": ["Python", "SQL", "Git", "OOP", "REST APIs", "Streamlit", "Testing", "Debugging"],
    "general": ["Communication", "Teamwork", "Problem solving", "Time management", "MS Office", "Leadership"],
}
SAMPLE = dict(name="Diya Agarwal", role="Retail Sales Associate", email="diya@example.com",
              phone="+91 98765 43210", location="New Delhi, India",
              summary="Customer-focused sales professional with a strong record of exceeding targets.",
              skills="Cash register operation, Inventory management, Teamwork, Sales expertise",
              languages="Hindi, English")
SAMPLE_EXP = [{"title": "Retail Sales Associate", "company": "ZARA, New Delhi", "dates": "2017 - Present",
               "bullets": "Increased monthly sales by 10% through upselling\nMaintained accurate store inventory"}]
SAMPLE_EDU = [{"degree": "Diploma in Financial Accounting", "school": "Oxford Software Institute", "year": "2016"}]

CSS = """*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;color:#222;font-size:13px;line-height:1.5}
.page{width:794px;min-height:1123px;background:#fff}h1{margin:0;font-size:34px;line-height:1.1}
h3{margin:18px 0 6px;font-size:12px;color:var(--a);letter-spacing:.08em;text-transform:uppercase;border-bottom:1px solid #ddd;padding-bottom:3px}
p{margin:4px 0}ul{margin:4px 0 0 18px;padding:0}li{margin:2px 0}.row{display:flex;justify-content:space-between}
.sub{color:#555;font-style:italic}.it{margin:8px 0}.ini{display:none}
.tag{display:inline-block;border:1px solid #ccc;border-radius:3px;padding:1px 8px;margin:2px 3px 2px 0;font-size:12px}
.d-banner .hd{background:var(--a);color:#fff;padding:32px 40px;display:flex;gap:20px;align-items:center}
.d-banner .ini{display:block;border:2px solid #fff;padding:10px 12px;font-size:28px;font-weight:700}
.d-banner .bd{padding:6px 40px 40px}
.d-classic{font-family:Georgia,serif}.d-classic .hd{text-align:center;padding:38px 40px 6px}
.d-classic h1{font-weight:400;letter-spacing:.12em;text-transform:uppercase;color:var(--a)}.d-classic .bd{padding:0 44px 40px}
.d-minimal .hd{margin:40px 44px 0;padding-left:16px;border-left:8px solid var(--a)}.d-minimal h1{color:var(--a)}.d-minimal .bd{padding:0 44px 40px}
.d-sidebar{display:grid;grid-template-columns:250px 1fr}.d-sidebar .sb{background:var(--a);color:#fff;padding:36px 22px}
.d-sidebar .sb h3{color:#fff;border-color:rgba(255,255,255,.4)}.d-sidebar .sb .tag{border-color:rgba(255,255,255,.5)}
.d-sidebar .ini{display:block;font-size:40px;font-weight:700;margin-bottom:10px}.d-sidebar .mn{padding:36px 32px}
.ph{object-fit:cover;display:block}.d-banner .ph{width:96px;height:118px;border:2px solid #fff}
.d-sidebar .ph{width:130px;height:150px;margin-bottom:12px;border:2px solid rgba(255,255,255,.7)}
.d-photo .top{height:14px;background:var(--a)}.d-photo .hd{display:flex;gap:22px;padding:26px 40px 8px;align-items:center}
.d-photo .ph,.d-photo .ini{display:flex;width:96px;height:118px;border-radius:3px;background:#e6e8ee;color:var(--a);font-size:30px;font-weight:700;align-items:center;justify-content:center}
.d-photo h1{color:var(--a);font-size:30px}.d-photo .bd{padding:6px 40px 40px}
.r{display:grid;grid-template-columns:120px 1fr;gap:16px;border-top:2px solid var(--a);padding:12px 0}
.r h4{margin:0;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.att{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}
.att figure{margin:0;border:1px solid #ddd;padding:4px;text-align:center;font-size:11px;color:#555}
.att img{width:100%;height:150px;object-fit:contain;display:block;background:#fafafa}
.yr{color:#555}"""


# ---------- rendering ----------
def _lines(t):
    return [l.strip(" -•*\t") for l in (t or "").splitlines() if l.strip(" -•*\t")]


def _ul(t):
    ls = _lines(t)
    return "<ul>" + "".join(f"<li>{esc(l)}</li>" for l in ls) + "</ul>" if ls else ""


def _tags(t):
    return "".join(f'<span class="tag">{esc(s.strip())}</span>' for s in (t or "").replace("\n", ",").split(",") if s.strip())


def _sec(title, body):
    return f"<h3>{title}</h3>{body}" if body else ""


MONTHS = ["Select", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _norm(e):
    """Turn the structured job form (month/year dropdowns, city, country) into display text."""
    c = lambda v: "" if v in (None, "", "Select") else str(v)
    start = " ".join(x for x in (c(e.get("smonth")), c(e.get("syear"))) if x)
    end = "Present" if e.get("current") else " ".join(x for x in (c(e.get("emonth")), c(e.get("eyear"))) if x)
    dates = (f"{start} - {end}" if start and end else start or end) or e.get("dates", "")
    company = ", ".join(x for x in (e.get("company"), e.get("city"), e.get("country")) if x)
    return {"title": e.get("title", ""), "company": company, "dates": dates, "bullets": e.get("bullets", "")}


def render_html(d, exp, edu, design, accent, scale=1.0, fit=False):
    exp = [_norm(e) for e in exp]
    name = esc(d.get("name") or "Your Name")
    ini = "".join(w[0] for w in (d.get("name") or "YN").split()[:2]).upper()
    role = esc(d.get("role", ""))
    exp_h = "".join(
        f'<div class="it"><div class="row"><b>{esc(e.get("title", ""))}</b><span>{esc(e.get("dates", ""))}</span></div>'
        f'<div class="sub">{esc(e.get("company", ""))}</div>{_ul(e.get("bullets"))}</div>' for e in exp if any(e.values()))
    edu_h = "".join(
        f'<div class="it"><div><b>{esc(e.get("degree", ""))}</b>'
        + (f' <span class="yr">({esc(e["year"])})</span>' if e.get("year") else "")
        + f'</div><div class="sub">{esc(e.get("school", ""))}</div></div>' for e in edu if any(e.values()))
    summ = f"<p>{esc(d['summary'])}</p>" if d.get("summary") else ""
    skills, langs = _tags(d.get("skills")), _tags(d.get("languages"))
    certs, proj = _ul(d.get("certifications")), _ul(d.get("projects"))
    photo = d.get("photo")
    pic = f'<img class="ph" src="{photo}">' if photo else f'<div class="ini">{ini}</div>'
    figs = "".join(f'<figure><img src="{a["uri"]}"><figcaption>{esc(a["name"])}</figcaption></figure>'
                   for a in d.get("attachments") or [])
    att = f'<div class="att">{figs}</div>' if figs else ""
    if design == "sidebar":
        contact = "".join(f"<p>{esc(x)}</p>" for x in (d.get("email"), d.get("phone"), d.get("location")) if x)
        body = (f'<div class="sb">{pic}' + _sec("Contact", contact) + _sec("Skills", skills)
                + _sec("Languages", langs) + _sec("Certifications", certs) + '</div><div class="mn">'
                + f'<h1 style="color:var(--a)">{name}</h1><div class="sub">{role}</div>'
                + _sec("Summary", summ) + _sec("Experience", exp_h) + _sec("Education", edu_h) + _sec("Projects", proj)
                + _sec("Certificates & achievements", att) + "</div>")
    elif design == "photo":
        contact = "<br>".join(esc(x) for x in (d.get("location"), d.get("phone"), d.get("email")) if x)
        rows = [("Summary", summ), ("Skills", skills), ("Experience", exp_h), ("Education", edu_h), ("Projects", proj),
                ("Certifications", certs), ("Languages", langs), ("Certificates & achievements", att)]
        body = ('<div class="top"></div><div class="hd">' + pic + f'<div><h1>{name}</h1><div>{role}</div>'
                f'<div class="sub">{contact}</div></div></div><div class="bd">'
                + "".join(f'<div class="r"><h4>{t}</h4><div>{b}</div></div>' for t, b in rows if b) + "</div>")
    else:
        hdpic = pic if design == "banner" else f'<div class="ini">{ini}</div>'
        contact = esc(" | ".join(x for x in (d.get("location"), d.get("phone"), d.get("email")) if x))
        body = (f'<div class="hd">{hdpic}<div><h1>{name}</h1><div>{role}</div><div>{contact}</div></div></div>'
                '<div class="bd">' + _sec("Summary", summ) + _sec("Skills", skills) + _sec("Experience", exp_h)
                + _sec("Education", edu_h) + _sec("Projects", proj) + _sec("Certifications", certs)
                + _sec("Languages", langs) + _sec("Certificates & achievements", att) + "</div>")
    if fit:  # scale the page to whatever width the preview box has, so nothing is cut off
        js = ("(function(){var p=document.querySelector('.page'),w=document.getElementById('w');"
              "function f(){var s=w.clientWidth/794;p.style.transform='scale('+s+')';w.style.height=(p.offsetHeight*s)+'px'}"
              "f();window.addEventListener('resize',f)})();")
        return (f"<style>{CSS}</style><div id='w' style='width:100%;overflow:hidden'>"
                f"<div class='page d-{design}' style='--a:{accent};transform-origin:0 0'>{body}</div></div><script>{js}</script>")
    return (f"<style>{CSS}</style><div style='width:{int(794 * scale)}px'>"
            f"<div class='page d-{design}' style='--a:{accent};transform:scale({scale});transform-origin:0 0'>{body}</div></div>")


# ---------- state helpers ----------
def _D():
    return st.session_state.setdefault("wz", {"exp": [{}], "edu": [{}]})


def _f(label, name, area=False, **kw):
    D, key = _D(), f"w_{name}"
    if key not in st.session_state:
        st.session_state[key] = D.get(name, "")
    v = (st.text_area if area else st.text_input)(label, key=key, **kw)
    D[name] = v
    return v


def _entries(kind, fields, add_label):
    D = _D()
    for i, e in enumerate(D[kind]):
        with st.container(border=True):
            for field, label, area in fields:
                key = f"{kind}_{i}_{field}"
                if key not in st.session_state:
                    st.session_state[key] = e.get(field, "")
                e[field] = (st.text_area if area else st.text_input)(label, key=key, **({"height": 110} if area else {}))
            if len(D[kind]) > 1 and st.button("Remove this entry", key=f"rm_{kind}_{i}"):
                D[kind].pop(i)
                for k in [k for k in st.session_state if k.startswith(f"{kind}_")]:
                    del st.session_state[k]
                st.rerun()
    if st.button(add_label, key=f"add_{kind}"):
        D[kind].append({})
        st.rerun()


def _exp_entries():
    D = _D()
    y = datetime.now().year
    years = ["Select"] + [str(v) for v in range(y + 1, y - 50, -1)]
    defaults = {"title": "", "company": "", "city": "", "country": "", "smonth": "Select", "syear": "Select",
                "emonth": "Select", "eyear": "Select", "current": False, "bullets": ""}
    for i, e in enumerate(D["exp"]):
        k = lambda f: f"exp_{i}_{f}"
        for f, dv in defaults.items():
            if k(f) not in st.session_state:
                st.session_state[k(f)] = e.get(f, dv)
        cur = st.session_state[k("current")]
        with st.container(border=True):
            c1, c2 = st.columns(2)
            e["title"] = c1.text_input("Job title", key=k("title"), placeholder="e.g. Data Analyst")
            e["company"] = c2.text_input("Employer", key=k("company"))
            c3, c4 = st.columns(2)
            e["city"] = c3.text_input("City", key=k("city"))
            e["country"] = c4.text_input("Country", key=k("country"))
            a, b, c, d = st.columns(4)
            e["smonth"] = a.selectbox("Start month", MONTHS, key=k("smonth"))
            e["syear"] = b.selectbox("Start year", years, key=k("syear"))
            e["emonth"] = c.selectbox("End month", MONTHS, key=k("emonth"), disabled=cur)
            e["eyear"] = d.selectbox("End year", years, key=k("eyear"), disabled=cur)
            e["current"] = st.checkbox("I currently work here", key=k("current"))
            if (not e["current"] and "Select" not in (e["syear"], e["eyear"], e["smonth"], e["emonth"])
                    and (int(e["eyear"]), MONTHS.index(e["emonth"])) < (int(e["syear"]), MONTHS.index(e["smonth"]))):
                st.warning("The end date is before the start date.")
            e["bullets"] = st.text_area("Achievements (one per line)", key=k("bullets"), height=120,
                                        placeholder="Increased monthly sales by 10% through upselling")
            _enh_buttons(k("bullets"), "bullets", f"exp_{i}", k("title"))
            if len(D["exp"]) > 1 and st.button("Remove this job", key=f"rm_exp_{i}"):
                D["exp"].pop(i)
                for key in [key for key in st.session_state if key.startswith(("exp_", "orig_exp_"))]:
                    del st.session_state[key]
                st.rerun()
    if st.button("Add another job", key="add_exp"):
        D["exp"].append({})
        st.rerun()


def _sync():
    """Copy widget values into the wizard dict (used before changing step, since old widgets disappear)."""
    D = _D()
    for k, v in list(st.session_state.items()):
        if k.startswith("w_"):
            D[k[2:]] = v
        else:
            p = k.split("_")
            if len(p) == 3 and p[0] in ("exp", "edu") and p[1].isdigit() and int(p[1]) < len(D[p[0]]):
                D[p[0]][int(p[1])][p[2]] = v


def _go(delta):
    _sync()
    D, s = _D(), st.session_state.wz_step
    if delta > 0 and s == 1 and not (D.get("name", "").strip() and D.get("email", "").strip()):
        st.session_state.wz_err = "Enter your full name and email to continue."
        return
    st.session_state.wz_err = ""
    st.session_state.wz_step = max(0, min(len(STEPS) - 1, s + delta))


def _to_gallery():
    _sync()
    st.session_state.wz_step = 0


def _add_skills():
    cur = [s.strip() for s in st.session_state.get("w_skills", "").split(",") if s.strip()]
    for s in st.session_state.get("pick", []):
        if s.lower() not in [c.lower() for c in cur]:
            cur.append(s)
    st.session_state["w_skills"] = ", ".join(cur)
    st.session_state["pick"] = []


def _data(D):
    exp = "\n\n".join(f"{e.get('title', '')} | {e.get('company', '')} | {e.get('dates', '')}\n{e.get('bullets', '')}"
                      for e in map(_norm, D["exp"]) if any(e.values()))
    edu = "\n".join(f"{e.get('degree', '')} - {e.get('school', '')} ({e.get('year', '')})" for e in D["edu"] if any(e.values()))
    keys = ["name", "email", "phone", "location", "role", "skills", "summary", "projects", "certifications", "languages"]
    out = {k: (D.get(k) or "").strip() for k in keys}
    out.update(template=DESIGNS[D.get("design", "banner")][1], education=edu, experience=exp)
    return out


def _uri(file, max_px, quality):
    import base64
    import io
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(file)).convert("RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _bytes(uri):
    import base64
    return base64.b64decode(uri.split(",", 1)[1])


def _view(D):
    """Resume data for display: text fields plus the photo and attachments (these are not sent to the PDF/database)."""
    return {**_data(D), "photo": D.get("photo"), "attachments": D.get("atts", [])}


def _reset_uploaders():
    D = _D()
    D["pv"] = D.get("pv", 0) + 1


def _rm_photo():
    _D().pop("photo", None)
    _reset_uploaders()


def _rm_att(i):
    _D().get("atts", []).pop(i)
    _reset_uploaders()


def _photo_ui():
    D = _D()
    st.markdown("**Photo (optional)**")
    st.caption("A passport-size photo works best. It appears in the Photo, Banner and Sidebar templates.")
    up = st.file_uploader("Upload a photo", type=["png", "jpg", "jpeg"], key=f"up_photo_{D.get('pv', 0)}",
                          label_visibility="collapsed")
    if up is not None:
        D["photo"] = _uri(up, 400, 85)
    if D.get("photo"):
        c1, c2 = st.columns([1, 3])
        c1.image(_bytes(D["photo"]), width=90)
        c2.button("Remove photo", on_click=_rm_photo)


def _attach_ui():
    D = _D()
    atts = D.setdefault("atts", [])
    st.markdown("**Certificates, achievements and other pictures (optional)**")
    st.caption("Add images of certificates, awards or work samples. Up to 8. They appear at the end of your resume.")
    files = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True,
                             key=f"up_att_{D.get('pv', 0)}", label_visibility="collapsed")
    for f in files or []:
        fid = f"{f.name}-{f.size}"
        if len(atts) < 8 and fid not in [a["id"] for a in atts]:
            atts.append({"id": fid, "name": f.name.rsplit(".", 1)[0], "uri": _uri(f, 700, 72)})
    if atts:
        cols = st.columns(4)
        for i, a in enumerate(atts):
            with cols[i % 4]:
                st.image(_bytes(a["uri"]), caption=a["name"], width=110)
                st.button("Remove", key=f"rma_{i}", on_click=_rm_att, args=(i,))


def _jump(i):
    _sync()
    st.session_state.wz_err = ""
    st.session_state.wz_step = i


TASKS = {
    "bullets": "Rewrite each line as a professional resume bullet that starts with a strong action verb. Keep the same facts. "
               "Do not invent numbers, tools or responsibilities. Return one bullet per line, no numbering.",
    "summary": "Rewrite this resume summary to be professional and concise (at most 3 sentences). Use only the facts given. "
               "Do not invent achievements.",
}


def _enhance(key, kind):
    import ai_helper
    from resume_utils import improve_bullet
    text = st.session_state.get(key, "").strip()
    if not text:
        st.session_state.wz_msg = "Write something first, then enhance it."
        return
    if kind == "summary":
        fallback = text
    else:
        fallback = "\n".join(improve_bullet(l.strip(" -•*\t")) for l in text.splitlines() if l.strip(" -•*\t"))
    result, used = ai_helper.ask(TASKS["summary" if kind == "summary" else "bullets"], text, fallback)
    st.session_state[f"orig_{key}"] = text
    st.session_state[key] = (result or text).strip()
    st.session_state.wz_msg = ("Enhanced with AI. Read it through and make sure every line is true." if used else
                               f"AI is not connected ({ai_helper.last_error}), so only the basic rewriter was used. "
                               "Open AI Resume Coach in the sidebar to set it up.")


def _suggest(title_key, bullets_key):
    import ai_helper
    title = st.session_state.get(title_key, "").strip()
    if not title:
        st.session_state.wz_msg = "Enter a job title first."
        return
    text, used = ai_helper.ask("Write 4 resume bullet ideas for this job title. Start each with a strong action verb. "
                               "Write [X] wherever a number would go. One per line, no numbering.", title, "")
    if not used:
        st.session_state.wz_msg = f"AI is not connected ({ai_helper.last_error}). Open AI Resume Coach in the sidebar to set it up."
        return
    cur = st.session_state.get(bullets_key, "").strip()
    st.session_state[bullets_key] = (cur + "\n" if cur else "") + text.strip()
    st.session_state.wz_msg = "Draft ideas added. Replace every [X] and edit each line so it matches what you really did."


def _undo(key):
    if f"orig_{key}" in st.session_state:
        st.session_state[key] = st.session_state.pop(f"orig_{key}")


def _enh_buttons(key, kind, tag, title_key=None):
    c1, c2, c3 = st.columns([2.2, 1, 2])
    c1.button("✨ Enhance with AI", key=f"enh_{tag}", on_click=_enhance, args=(key, kind))
    if f"orig_{key}" in st.session_state:
        c2.button("Undo", key=f"undo_{tag}", on_click=_undo, args=(key,))
    if title_key:
        c3.button("Suggest ideas", key=f"sug_{tag}", on_click=_suggest, args=(title_key, key))


def _parse_saved(saved):
    """Rebuild wizard state from a saved resume (text fields only)."""
    D = {"exp": [], "edu": []}
    for k in ["name", "email", "phone", "location", "role", "skills", "summary", "projects", "certifications", "languages"]:
        D[k] = saved.get(k, "") or ""
    for block in re.split(r"\n\s*\n", (saved.get("experience") or "").strip()):
        if not block.strip():
            continue
        head, _, rest = block.partition("\n")
        parts = [p.strip() for p in head.split("|")]
        if len(parts) == 3:
            e = {"title": parts[0], "company": parts[1], "bullets": rest.strip()}
            m = re.match(r"(\w{3}) (\d{4}) - (?:(\w{3}) (\d{4})|Present)$", parts[2])
            if m and m[1] in MONTHS:
                e.update(smonth=m[1], syear=m[2])
                if m[3]:
                    e.update(emonth=m[3], eyear=m[4])
                else:
                    e["current"] = True
            else:
                e["dates"] = parts[2]
        else:
            e = {"bullets": block.strip()}
        D["exp"].append(e)
    for line in (saved.get("education") or "").splitlines():
        m = re.match(r"(.*?) - (.*?) \((.*)\)$", line.strip())
        D["edu"].append({"degree": m[1], "school": m[2], "year": m[3]} if m else {"degree": line.strip()})
    D["exp"], D["edu"] = D["exp"] or [{}], D["edu"] or [{}]
    return D


def _persist(user, data, D, save_resume, as_new=False):
    """Save text via your save_resume(); update the same row when editing; keep photo + attachments in resume_media."""
    from database import connect
    rid, updated = (None if as_new else D.get("rid")), False
    if rid:
        with connect() as c:
            cur = c.execute("UPDATE resumes SET name=?, email=?, data_json=? WHERE id=? AND user_id=?",
                            (data["name"], data["email"], json.dumps(data), rid, user["id"]))
            updated = cur.rowcount > 0
    if not updated:
        rid = save_resume(user["id"], data)
    D["rid"] = rid
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS resume_media (resume_id INTEGER PRIMARY KEY, photo TEXT, atts_json TEXT, "
                  "FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE CASCADE)")
        c.execute("INSERT OR REPLACE INTO resume_media(resume_id, photo, atts_json) VALUES(?,?,?)",
                  (rid, D.get("photo"), json.dumps(D.get("atts", []))))
    return rid, updated


def _load_media(rid, uid):
    import sqlite3
    from database import connect
    try:
        with connect() as c:
            row = c.execute("SELECT m.photo, m.atts_json FROM resume_media m JOIN resumes r ON r.id = m.resume_id "
                            "WHERE m.resume_id=? AND r.user_id=?", (rid, uid)).fetchone()
    except sqlite3.OperationalError:  # table not created yet
        return None, []
    return (row[0], json.loads(row[1] or "[]")) if row else (None, [])


def _new():
    for k in [k for k in st.session_state if k.startswith(("w_", "exp_", "edu_", "orig_", "up_"))] + ["wz"]:
        st.session_state.pop(k, None)
    st.session_state.wz_step = 0


def edit_saved(saved, rid=None, uid=None):
    """Button callback for 'My Resumes': open a saved resume (with its photo and attachments) in the builder."""
    old = st.session_state.get("wz", {})
    D = _parse_saved(saved)
    D["design"], D["accent"] = old.get("design", "banner"), old.get("accent", ACCENTS["Crimson"])
    if rid:
        D["rid"] = rid
        photo, atts = _load_media(rid, uid)
        if photo:
            D["photo"] = photo
        D["atts"] = atts
    for k in [k for k in st.session_state if k.startswith(("w_", "exp_", "edu_", "orig_", "up_"))]:
        del st.session_state[k]
    st.session_state.wz, st.session_state.wz_step, st.session_state.page = D, 1, "Resume Builder"


# ---------- pages ----------
def _gallery(D):
    st.title("Choose a template")
    st.caption("Pick a design and a color. You can change both later.")
    names = list(ACCENTS)
    cur = list(ACCENTS.values()).index(D["accent"]) if D.get("accent") in ACCENTS.values() else 0
    color = st.radio("Color", names, index=cur, horizontal=True)
    D["accent"] = ACCENTS[color]
    use_real = bool(D.get("name"))
    data = _view(D) if use_real else SAMPLE
    exp, edu = (D["exp"], D["edu"]) if use_real else (SAMPLE_EXP, SAMPLE_EDU)
    data = {**data, "attachments": []}
    for col, (key, (label, _)) in zip(st.columns(4) + st.columns(4), DESIGNS.items()):
        with col:
            _show_html(render_html(data, exp, edu, key, D["accent"], fit=True), 345)
            if st.button(f"Use {label}", key=f"pick_{key}", use_container_width=True,
                         type="primary" if D.get("design") == key else "secondary"):
                D["design"] = key
                st.session_state.wz_step = 1
                st.rerun()


def render_resume_wizard(user, create_resume_pdf, save_resume):
    from ai_helper import ask as generate_ai_text
    from resume_utils import make_summary

    D = _D()
    D.setdefault("design", "banner")
    D.setdefault("accent", ACCENTS["Crimson"])
    st.session_state.setdefault("wz_step", 0)
    step = st.session_state.wz_step
    st.caption("Click any step to go back and edit it.")
    for i, (col, label) in enumerate(zip(st.columns(len(STEPS)), STEPS)):
        col.button(label, key=f"jump_{i}", on_click=_jump, args=(i,), type="primary" if i == step else "secondary",
                   use_container_width=True)
    if step == 0:
        return _gallery(D)

    left, right = st.columns([5, 4], gap="large")
    msg = st.session_state.pop("wz_msg", None)
    with left:
        if msg:
            st.info(msg)
        if step == 1:
            st.title("Let's start with your header")
            st.caption("Include your full name and ways for employers to reach you.")
            c1, c2 = st.columns(2)
            with c1:
                _f("Full name *", "name")
                _f("Email *", "email")
                _f("City / location", "location")
            with c2:
                _f("Target job title", "role", placeholder="e.g. Data Analyst")
                _f("Phone", "phone")
            _photo_ui()
        elif step == 2:
            st.title("Add your work experience")
            st.caption("Start with your most recent job. Choose dates from the dropdowns.")
            _exp_entries()
        elif step == 3:
            st.title("Now, add your education")
            _entries("edu", [("degree", "Degree / course", False), ("school", "School / institute", False),
                             ("year", "Year (e.g. 2020 - 2024)", False)], "Add another education")
        elif step == 4:
            st.title("Add your skills")
            r = (D.get("role") or "").lower()
            opts = SUGG["data"] if "data" in r else SUGG["web"] if ("web" in r or "front" in r) else \
                SUGG["python"] if ("python" in r or "develop" in r or "software" in r) else SUGG["general"]
            st.multiselect("Suggested for your role (add only what is true for you)", opts, key="pick")
            st.button("Add selected skills", on_click=_add_skills)
            _f("Your skills (comma separated)", "skills", area=True, height=120)
        elif step == 5:
            st.title("Write your summary")
            st.caption("Two or three sentences about who you are and what you offer.")
            if st.button("Write a draft for me"):
                data = _data(D)
                task = "Write a concise, truthful 3-sentence resume summary using only the supplied facts. Do not invent achievements."
                ctx = f"Name: {data['name']}\nRole: {data['role']}\nSkills: {data['skills']}\nEducation: {data['education']}"
                fb = make_summary(data["name"] or "Candidate", data["role"], data["skills"], data["education"])
                text, used = generate_ai_text(task, ctx, fb)
                st.session_state["w_summary"] = text
                st.toast("Draft added. Edit it so it sounds like you.")
            _f("Professional summary", "summary", area=True, height=160)
            _enh_buttons("w_summary", "summary", "summary")
        elif step == 6:
            st.title("Additional details")
            _f("Projects", "projects", area=True, height=120, placeholder="Project name: what you built, tools, result")
            _enh_buttons("w_projects", "bullets", "projects")
            _f("Certifications / achievements", "certifications", area=True, height=90)
            _f("Languages (comma separated)", "languages")
            _attach_ui()
        else:
            st.title("Finalize your resume")
            data = _data(D)
            st.caption("Check everything. Use Edit to change any section.")
            for ok, label, idx in [(data["name"] and data["email"], "Header", 1), (data["experience"], "Experience", 2),
                                   (data["education"], "Education", 3), (data["skills"], "Skills", 4),
                                   (data["summary"], "Summary", 5),
                                   (data["projects"] or data["certifications"] or data["languages"] or D.get("atts"), "Extras", 6)]:
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"{'✅' if ok else '⬜'} &nbsp;{label}")
                c2.button("Edit", key=f"edit_{idx}", on_click=_jump, args=(idx,), use_container_width=True)
            st.download_button("Download PDF", create_resume_pdf(data), "careerforge_resume.pdf", "application/pdf",
                               use_container_width=True)
            page = render_html(_view(D), D["exp"], D["edu"], D["design"], D["accent"])
            st.download_button("Download as web page (.html)", f"<!doctype html><meta charset='utf-8'>{page}",
                               "careerforge_resume.html", "text/html", use_container_width=True)
            if D.get("rid"):
                c1, c2 = st.columns(2)
                if c1.button("Save changes", type="primary", use_container_width=True):
                    rid, updated = _persist(user, data, D, save_resume)
                    st.success(f"Changes saved to resume #{rid}." if updated else f"Saved as resume #{rid}.")
                if c2.button("Save as new copy", use_container_width=True):
                    st.success(f"Saved as new resume #{_persist(user, data, D, save_resume, as_new=True)[0]}.")
            elif st.button("Save to my account", use_container_width=True):
                st.success(f"Resume saved to your account (ID {_persist(user, data, D, save_resume)[0]}).")
            st.button("Start a new resume", on_click=_new)
            st.caption("Photos and attachments are saved with your resume. The PDF uses your app's existing layout and does not include them. The .html download matches the preview exactly, pictures included: open it and press Ctrl + P to save a PDF with images.")

        if st.session_state.get("wz_err"):
            st.error(st.session_state.wz_err)
        b1, b2 = st.columns(2)
        b1.button("Back", on_click=_go, args=(-1,), use_container_width=True)
        if step < len(STEPS) - 1:
            b2.button("Continue", on_click=_go, args=(1,), type="primary", use_container_width=True)

    with right:
        names = list(ACCENTS)
        cur = names[list(ACCENTS.values()).index(D["accent"])] if D["accent"] in ACCENTS.values() else names[0]
        D["accent"] = ACCENTS[st.selectbox("Color", names, index=names.index(cur))]
        _show_html(render_html(_view(D), D["exp"], D["edu"], D["design"], D["accent"], fit=True), 640)
        st.button("Change template", on_click=_to_gallery, use_container_width=True)

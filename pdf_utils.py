import io
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

def create_resume_pdf(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=46, leftMargin=46, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    accent = {"Modern": "#2563eb", "Simple": "#222222", "Creative": "#7c3aed"}.get(data.get("template"), "#2563eb")
    name_style = ParagraphStyle("Candidate", parent=styles["Title"], fontName="Helvetica-Bold",
                                fontSize=22, leading=26, textColor=colors.HexColor(accent), alignment=TA_CENTER, spaceAfter=8)
    head = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=11, leading=14,
                          textColor=colors.HexColor(accent), spaceBefore=12, spaceAfter=5)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=13)
    story = [Paragraph(escape(data.get("name","Resume")), name_style)]
    contact = " | ".join(filter(None, [data.get("email",""), data.get("phone",""), data.get("location","")]))
    if contact:
        story.extend([Paragraph(escape(contact), body), Spacer(1, 10)])
    for title, key in [
        ("Professional Summary","summary"),("Education","education"),("Skills","skills"),
        ("Projects","projects"),("Experience","experience"),
        ("Certifications & Achievements","certifications"),("Languages","languages")
    ]:
        value = data.get(key, "").strip()
        if value:
            story.append(Paragraph(escape(title), head))
            story.append(Paragraph(escape(value).replace("\n","<br/>"), body))
            story.append(HRFlowable(width="100%", thickness=.4, color=colors.lightgrey, spaceBefore=6))
    doc.build(story)
    return buffer.getvalue()

# CareerForge — AI Career & Resume Studio

A local Streamlit resume-builder learning project.

## Included features
- Sign up and login with salted PBKDF2 password hashes
- Resume builder with Modern, Simple and Creative styles
- Live HTML preview and PDF export
- Save, reopen and delete multiple resumes using local SQLite
- Job-description keyword coverage analyzer (transparent heuristic, not a commercial ATS score)
- Professional-summary and bullet-point writing helpers
- Role-based starter skill-gap checklist
- Gemini-powered AI Resume Coach and writing suggestions; built-in fallback works without an API key

## Requirements
- Windows 10/11
- Python 3.10 or newer
- Internet connection for installing Python packages (not required to run after installation)

## Run on Windows (PowerShell)
1. Extract this ZIP.
2. Open the extracted `CareerForge_AI_Resume_Builder` folder in VS Code.
3. In the VS Code terminal run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If PowerShell blocks activation, skip the activation line and run the two `py -m pip` / `py -m streamlit` commands. Open the Local URL shown in the terminal, usually `http://localhost:8501`.

## Gemini AI setup
1. Copy `.env.example` and rename the copy to `.env`.
2. Add your own key: `GEMINI_API_KEY=your_key_here`.
3. Optionally set `GEMINI_MODEL=gemini-flash-latest (optional; omit to use automatic model discovery)`.
4. Restart Streamlit.

Never share your API key or commit `.env` to GitHub. API usage may cost money. Without a key, AI features show a clear setup message or local fallback where supported.

## Data storage
The app creates `careerforge.db` in this folder on first run. It stores account and resume data locally on this computer. Back up this file if you need to preserve your records.

## Important limitations
- ATS result is keyword coverage only; it is not a real ATS vendor score and does not assess semantic fit.
- Skill-gap suggestions are a small curated starter list, not a full labor-market analysis.
- AI writing requires your own Gemini API key and may incur charges.
- This is an academic/minor-project prototype. Streamlit Cloud deployment requires GEMINI_API_KEY in App settings → Secrets. SQLite on ephemeral hosting is not durable; use a managed database for production. Gmail OAuth currently requires additional cloud OAuth configuration.

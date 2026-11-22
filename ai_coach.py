"""AI Resume Coach page: chat, resume review, and tailoring to a job description."""
import streamlit as st

import ai_helper


def _setup_help():
    st.markdown("**Pick one option, add the line to your `.env` file (in the project folder), then restart the app.**")
    a, b, c, d = st.tabs(["Free on your PC", "Gemini", "OpenAI", "Claude"])
    with a:
        st.markdown("Install **Ollama** from ollama.com, then run `ollama pull llama3.2` in a terminal. Add this line:")
        st.code("OLLAMA_MODEL=llama3.2", language="text")
    with b:
        st.markdown("Create a key in **Google AI Studio** (a free tier is available). Add:")
        st.code("GEMINI_API_KEY=your-key-here", language="text")
    with c:
        st.markdown("Create a key at platform.openai.com. Add:")
        st.code("OPENAI_API_KEY=sk-your-key-here", language="text")
    with d:
        st.markdown("Create a key at console.anthropic.com, run `pip install anthropic`, then add:")
        st.code("ANTHROPIC_API_KEY=your-key-here", language="text")
    st.caption("Keep your key private: never share your .env file or upload it to GitHub. Optional: add AI_MODEL=model-name to choose a different model.")


def render_ai_coach():
    from resume_wizard import _D, _data

    st.title("AI Resume Coach")
    st.caption("Get advice, a full resume review, or help tailoring your resume to a job.")
    stat = ai_helper.status()
    if not stat:
        st.warning("AI is not connected yet. It takes about two minutes to set up.")
        _setup_help()
        return
    st.caption(f"Connected: {stat}")
    with st.expander("Change AI provider"):
        _setup_help()

    d = _data(_D())
    resume = "\n".join(f"{k}: {v}" for k, v in d.items() if v and k != "template") or "(The user has not filled in a resume yet.)"
    system = ("You are CareerForge's friendly, honest resume coach. Give concrete, concise advice. Never invent experience, "
              "skills or numbers; if something is missing, ask the user for it. The user's current resume:\n" + resume)

    def run(prompt, history=None):
        try:
            with st.spinner("Thinking..."):
                return ai_helper.chat((history or []) + [{"role": "user", "content": prompt}], system, max_tokens=1000)
        except Exception as ex:
            st.error(f"The AI request failed: {str(ex)[:200]}")

    chat_tab, review_tab, tailor_tab = st.tabs(["Chat", "Review my resume", "Tailor to a job"])
    with chat_tab:
        msgs = st.session_state.setdefault("coach_msgs", [])
        if not msgs:
            st.info("Try: \"How can I make my first job sound stronger?\" or \"What skills should a data analyst list?\"")
        for m in msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
        if prompt := st.chat_input("Ask the coach anything about your resume or job search"):
            with st.chat_message("user"):
                st.markdown(prompt)
            reply = run(prompt, msgs[-10:])
            if reply:
                msgs += [{"role": "user", "content": prompt}, {"role": "assistant", "content": reply}]
                st.rerun()
        if msgs and st.button("Clear chat"):
            st.session_state.coach_msgs = []
            st.rerun()
    with review_tab:
        st.write("The coach reads the resume you built in Resume Builder and gives honest feedback.")
        if st.button("Review my resume", type="primary"):
            st.session_state.coach_review = run(
                "Review my resume. Give: 1) overall impression in 2 sentences, 2) three strongest points, "
                "3) five specific improvements, 4) a score out of 10 with a one-line reason. Be honest and specific.")
        if st.session_state.get("coach_review"):
            st.markdown(st.session_state.coach_review)
    with tailor_tab:
        job = st.text_area("Paste the job description", height=200)
        if st.button("Tailor my resume", type="primary"):
            if not job.strip():
                st.warning("Paste a job description first.")
            else:
                st.session_state.coach_tailor = run(
                    "Compare my resume with this job description.\n\n" + job +
                    "\n\nGive: 1) a match score out of 10, 2) important keywords I could add ONLY if they are true for me, "
                    "3) a rewritten summary using only facts from my resume, 4) three achievements from my resume to emphasize. "
                    "Do not invent anything.")
        if st.session_state.get("coach_tailor"):
            st.markdown(st.session_state.coach_tailor)

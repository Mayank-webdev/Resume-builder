"""Gemini-only AI integration for CareerForge.

Configure GEMINI_API_KEY in Streamlit Cloud Secrets or local .env.
Optional: GEMINI_MODEL may select a model available to your API key.
"""
import os
import re
import time
from openai import OpenAI

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
last_error = ""
_cached_model = None


def _cfg():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None, None
    return "Gemini", (os.getenv("GEMINI_MODEL") or os.getenv("AI_MODEL") or _cached_model or "gemini-flash-latest").strip()


def status():
    name, model = _cfg()
    return f"{name} - {model}" if name else None


def _client():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to Streamlit Cloud → App settings → Secrets.")
    return OpenAI(api_key=key, base_url=GEMINI_URL)


def _discover_gemini(client):
    global _cached_model
    # Use Google's model listing API via the GenAI SDK only when the default alias is unavailable.
    from google import genai
    catalog = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "").strip())
    ids = [m.name.replace("models/", "") for m in catalog.models.list()]
    flash = [m for m in ids if re.fullmatch(r"gemini-\d+(?:\.\d+)?-flash(?:-\w+)?", m)]
    if not flash:
        raise RuntimeError("No Gemini Flash model is available for this API key. Check Google AI Studio model access.")
    _cached_model = sorted(flash)[-1]
    return _cached_model


def _call(messages, system="", max_tokens=1000):
    name, model = _cfg()
    if not name:
        raise RuntimeError("Gemini is not connected. Add GEMINI_API_KEY to Streamlit Cloud Secrets.")
    client = _client()
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    # Retry transient overload/rate-limit/server errors with backoff.
    delays = (1.5, 3, 6, 10)
    last = None
    for attempt in range(5):
        try:
            result = client.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=max_tokens,
            )
            return result.choices[0].message.content or ""
        except Exception as exc:
            last = exc
            code = getattr(exc, "status_code", None)
            if code == 404 and not os.getenv("GEMINI_MODEL") and not os.getenv("AI_MODEL") and attempt == 0:
                model = _discover_gemini(client)
                continue
            if code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(delays[attempt])
                continue
            raise
    raise last


def chat(messages, system="", max_tokens=1000):
    try:
        return _call(messages, system, max_tokens)
    except Exception as exc:
        detail = ""
        try:
            detail = exc.response.text[:250]
        except Exception:
            pass
        hint = ""
        code = getattr(exc, "status_code", None)
        if code == 503:
            hint = " Gemini is temporarily overloaded; retry in a minute."
        elif code == 429:
            hint = " Gemini rate limit/quota reached; check your Google AI Studio quota."
        elif code == 401 or code == 400:
            hint = " Check that GEMINI_API_KEY is valid and enabled for the Gemini API."
        elif code == 404:
            hint = " The configured model was not found; remove GEMINI_MODEL to use automatic model selection."
        raise RuntimeError(f"{type(exc).__name__}: {str(exc)[:180]} {detail}{hint}".strip()) from exc


def ask(task, context, fallback=""):
    global last_error
    last_error = ""
    try:
        answer = chat(
            [{"role": "user", "content": f"{task}\n\n---\n{context}"}],
            system="You are CareerForge's professional resume and career assistant. Never invent facts, skills, metrics, employers or experience. Be specific, helpful and truthful. Return only the requested content.",
        )
        return (answer or fallback).strip(), bool(answer)
    except Exception as exc:
        last_error = str(exc)[:500]
        return fallback, False

"""Gemini-native AI integration for CareerForge.

Uses Google's official google-genai SDK and native Gemini API authentication.
This supports current Google AI Studio authorization keys (including AQ.-format keys).
Configure GEMINI_API_KEY in Streamlit Cloud Secrets or local .env.
Optional: GEMINI_MODEL may select a model available to your API key.
"""
import os
import re
import time

last_error = ""
_cached_model = None


def _cfg():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return None, None
    model = (os.getenv("GEMINI_MODEL") or os.getenv("AI_MODEL") or _cached_model or "gemini-2.5-flash-lite").strip()
    return "Gemini", model


def status():
    name, model = _cfg()
    return f"{name} - {model}" if name else None


def _client():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY to Streamlit Cloud → App settings → Secrets.")
    from google import genai
    return genai.Client(api_key=key)


def _discover_gemini(client):
    global _cached_model
    models = list(client.models.list())
    names = [getattr(m, "name", "").replace("models/", "") for m in models]
    flash = [n for n in names if re.fullmatch(r"gemini-\d+(?:\.\d+)?-flash(?:-lite)?(?:-\w+)?", n)]
    if not flash:
        raise RuntimeError("No Gemini Flash model is available for this API key. Check Google AI Studio model access.")
    # Prefer Flash Lite to reduce free-tier request cost; otherwise use a listed Flash model.
    lite = [n for n in flash if "lite" in n]
    _cached_model = sorted(lite or flash)[-1]
    return _cached_model


def _contents(messages):
    """Convert OpenAI-style chat history into Gemini Content objects."""
    from google.genai import types
    result = []
    for message in messages:
        role = message.get("role", "user")
        if role == "system":
            continue
        gemini_role = "model" if role == "assistant" else "user"
        text = message.get("content", "")
        if isinstance(text, list):
            text = "\n".join(str(part.get("text", "")) for part in text if isinstance(part, dict))
        result.append(types.Content(role=gemini_role, parts=[types.Part.from_text(text=str(text))]))
    return result


def _call(messages, system="", max_tokens=1000):
    name, model = _cfg()
    if not name:
        raise RuntimeError("Gemini is not connected. Add GEMINI_API_KEY to Streamlit Cloud Secrets.")
    from google.genai import types
    client = _client()
    contents = _contents(messages)
    delays = (2, 4, 8, 12)
    last = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system or None,
                    max_output_tokens=max_tokens,
                    temperature=0.4,
                ),
            )
            answer = getattr(response, "text", None)
            if not answer:
                raise RuntimeError("Gemini returned an empty response. Try a shorter prompt.")
            return answer.strip()
        except Exception as exc:
            last = exc
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            message = str(exc).lower()
            if (code == 404 or "not found" in message) and not os.getenv("GEMINI_MODEL") and not os.getenv("AI_MODEL") and attempt == 0:
                model = _discover_gemini(client)
                continue
            if (code in (429, 500, 502, 503, 504) or any(x in message for x in ("429", "503", "resource_exhausted", "unavailable"))) and attempt < 4:
                time.sleep(delays[attempt])
                continue
            raise
    raise last


def chat(messages, system="", max_tokens=1000):
    try:
        return _call(messages, system, max_tokens)
    except Exception as exc:
        message = str(exc)
        low = message.lower()
        hint = ""
        if "429" in low or "resource_exhausted" in low or "quota" in low:
            hint = " Gemini free-tier quota/rate limit reached. Check Google AI Studio Rate limits."
        elif "503" in low or "unavailable" in low:
            hint = " Gemini is temporarily overloaded; try again later."
        elif "api key" in low or "invalid_argument" in low or "unauthenticated" in low or "401" in low:
            hint = " Check GEMINI_API_KEY in Streamlit Cloud Secrets. Create/copy it from Google AI Studio; never paste it into chat."
        elif "404" in low or "not found" in low:
            hint = " The selected Gemini model is unavailable to this key. Remove GEMINI_MODEL to use automatic model discovery."
        raise RuntimeError(f"{type(exc).__name__}: {message[:220]}{hint}") from exc


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

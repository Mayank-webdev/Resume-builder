"""One place for all AI calls. Put ONE of these in your .env file (see AI Resume Coach > Set up AI):
    OLLAMA_MODEL=llama3.2            (free, runs on your PC)
    GEMINI_API_KEY=...               (free tier available)
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=...            (needs: pip install anthropic)
Optional: AI_MODEL=<model name> to override the default model."""
import os
import re
import time

last_error = ""
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_gemini_model = None  # filled in automatically if the default model name is not found


def _cfg():
    e = os.getenv
    if e("ANTHROPIC_API_KEY"):
        return "Claude", e("AI_MODEL") or "claude-haiku-5-5"
    if e("OPENAI_API_KEY"):
        return "OpenAI", e("AI_MODEL") or "gpt-4o-mini"
    if e("GEMINI_API_KEY"):
        return "Gemini", e("AI_MODEL") or _gemini_model or "gemini-flash-latest"
    if e("OLLAMA_MODEL"):
        return "Ollama (local)", e("OLLAMA_MODEL")
    return None, None


def status():
    """'Claude - model' style text when AI is configured, else None."""
    name, model = _cfg()
    return f"{name} - {model}" if name else None


def _discover_gemini(client):
    """Ask Google which models this key can use and pick the newest 'flash' one."""
    global _gemini_model
    ids = [m.id.replace("models/", "") for m in client.models.list()]
    flash = [i for i in ids if re.fullmatch(r"gemini-\d+(\.\d+)?-flash", i)]
    if not flash:
        raise RuntimeError("No Gemini flash model found for this key. Models seen: " + ", ".join(ids[:8]))
    _gemini_model = max(flash, key=lambda i: float(re.search(r"gemini-(\d+(?:\.\d+)?)", i).group(1)))
    return _gemini_model


def _call(messages, system="", max_tokens=800):
    name, model = _cfg()
    if not name:
        raise RuntimeError("AI is not set up yet.")
    if name == "Claude":
        import anthropic
        kw = {"system": system} if system else {}
        r = anthropic.Anthropic().messages.create(model=model, max_tokens=max_tokens, messages=messages, **kw)
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    from openai import OpenAI
    extra = {}
    if name == "OpenAI":
        client = OpenAI()
    elif name == "Gemini":
        client = OpenAI(api_key=os.getenv("GEMINI_API_KEY"), base_url=GEMINI_URL)
        extra = {"reasoning_effort": "low"}  # keeps answers fast and leaves room for the reply
        max_tokens *= 2
    else:
        client = OpenAI(api_key="ollama", base_url=os.getenv("OLLAMA_URL", "http://localhost:11434/v1"))
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    discovered = False
    fallback = ["gemini-flash-lite-latest"] if name == "Gemini" and not os.getenv("AI_MODEL") else []
    delay = 2
    for attempt in range(5):
        try:
            r = client.chat.completions.create(model=model, messages=msgs, max_tokens=max_tokens, **extra)
            return r.choices[0].message.content
        except Exception as ex:
            code = getattr(ex, "status_code", None)
            if code == 404 and name == "Gemini" and not os.getenv("AI_MODEL") and not discovered:
                model, discovered = _discover_gemini(client), True  # default name unavailable: use one that is
                continue
            if code in (429, 500, 502, 503, 504) and attempt < 4:  # provider is busy: wait and retry
                if attempt == 2 and fallback:
                    model = fallback.pop()  # still busy: try the lighter model
                time.sleep(delay)
                delay *= 1.5
                continue
            raise


def chat(messages, system="", max_tokens=800):
    """Same as _call, but the error message includes the provider's own explanation."""
    try:
        return _call(messages, system, max_tokens)
    except RuntimeError:
        raise
    except Exception as ex:
        detail = ""
        try:
            detail = ex.response.text[:300]
        except Exception:
            pass
        hint = ""
        name = _cfg()[0]
        if name == "Gemini" and "400" in str(ex):
            hint = " (Gemini returns 400 when the API key is wrong - check GEMINI_API_KEY in .env)"
        if "503" in str(ex) or "429" in str(ex):
            hint = " (the AI service is busy or you hit its free limit - wait a minute and try again)"
        if name == "Gemini" and "404" in str(ex):
            hint = " (model not found - add AI_MODEL=<a model name from Google AI Studio> to .env)"
        raise RuntimeError(f"{type(ex).__name__}: {str(ex)[:150]} {detail}{hint}".strip()) from ex


def ask(task, context, fallback=""):
    """Same shape as generate_ai_text: returns (text, used_ai). Falls back to `fallback` if AI is unavailable."""
    global last_error
    last_error = ""
    try:
        text = chat([{"role": "user", "content": f"{task}\n\n---\n{context}"}],
                    system="You are a careful professional resume writer. Never invent facts, numbers or experience. "
                           "Return only the requested text, with no preface.")
        return (text or fallback).strip(), bool(text)
    except Exception as ex:  # missing key, no internet, wrong model name, quota...
        last_error = str(ex)[:400]
        return fallback, False

import json
import os
from typing import Any


def retrieve_external(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    """Retrieve current public web knowledge through Gemini Google Search grounding.

    This is intentionally optional: without GEMINI_API_KEY the application keeps its
    deterministic local runbook RAG fallback so monitoring/RCA remains available.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        prompt = f"""You are the external evidence retrieval stage for an incident-response system.
Search the public web for authoritative technical documentation relevant to this incident query.
Prefer official vendor documentation, standards, and primary technical sources over blogs.
Do not diagnose the incident. Return JSON with a single key `sources`, an array of up to {top_k} objects.
Each object must contain `title`, `content`, `url`, and `reason`.
Only include information that is directly useful for validating a possible root cause or safe diagnostic/remediation step.

INCIDENT QUERY:
{query[:12000]}"""
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        data = json.loads((response.text or "{}").strip())
        sources = data.get("sources", []) if isinstance(data, dict) else []
        if not isinstance(sources, list):
            return []

        grounding_urls: list[str] = []
        try:
            metadata = response.candidates[0].grounding_metadata
            for chunk in getattr(metadata, "grounding_chunks", []) or []:
                web = getattr(chunk, "web", None)
                uri = getattr(web, "uri", None) if web else None
                if uri:
                    grounding_urls.append(uri)
        except Exception:
            grounding_urls = []

        result: list[dict[str, Any]] = []
        for index, item in enumerate(sources[:top_k]):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "External technical source")).strip()
            content = str(item.get("content", "")).strip()
            url = str(item.get("url", "")).strip()
            if not url and index < len(grounding_urls):
                url = grounding_urls[index]
            if not content:
                continue
            result.append({
                "id": f"EXT-{index + 1}",
                "type": "external",
                "title": title,
                "content": content,
                "url": url,
                "reason": str(item.get("reason", "")),
                "retrieval_mode": "gemini_google_search",
                "score": round(max(0.01, 1.0 - index * 0.08), 4),
            })
        return result
    except Exception:
        return []

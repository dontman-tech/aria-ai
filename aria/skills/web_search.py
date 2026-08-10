"""Web search skill - searches the web for information."""

from __future__ import annotations

import logging
import re
from typing import Optional

from aria.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)


class WebSearchSkill(Skill):
    name = "web_search"
    description = "Search the web for information"
    patterns = [
        r"\bsearch (for|the web|google)\b",
        r"\bgoogle\b",
        r"\blook up\b",
        r"\bfind (me )?(info|information|about)\b",
    ]
    keywords = ["search", "google", "look up", "find information"]

    def execute(self, text: str) -> SkillResult:
        query = self._extract_query(text)
        if not query:
            return SkillResult(success=False, message="What should I search for, Boss?")

        # Try DuckDuckGo Instant Answer API (no key required)
        result = self._search_ddg(query)
        if result:
            return result

        # Fallback: provide a search URL
        url = f"https://duckduckgo.com/?q={re.sub(r'\\s+', '+', query)}"
        return SkillResult(
            success=True,
            message=f"I couldn't get a direct answer, but here's a search for '{query}': {url}",
            data={"query": query, "url": url},
        )

    def _extract_query(self, text: str) -> str:
        lower = text.lower()
        for trigger in ("search for", "search the web for", "google", "look up", "find information about", "find info about", "find me", "find"):
            if lower.startswith(trigger):
                return text[len(trigger):].strip().strip("?").strip()
        # If none matched, use the whole text minus obvious triggers
        for trigger in ("search", "google", "look up", "find"):
            if trigger in lower:
                idx = lower.index(trigger)
                return text[idx + len(trigger):].strip().strip("?").strip()
        return ""

    def _search_ddg(self, query: str) -> Optional[SkillResult]:
        try:
            import urllib.parse
            import urllib.request
            import json

            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "ARIA/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            abstract = data.get("AbstractText", "")
            if abstract:
                source = data.get("AbstractSource", "")
                msg = f"Here's what I found, Boss: {abstract}"
                if source:
                    msg += f" (Source: {source})"
                return SkillResult(success=True, message=msg, data={"query": query, "abstract": abstract})

            # Try related topics
            topics = data.get("RelatedTopics", [])
            if topics and isinstance(topics[0], dict):
                first = topics[0].get("Text", "")
                if first:
                    return SkillResult(success=True, message=f"Here's what I found, Boss: {first}", data={"query": query})
        except Exception as e:
            logger.debug("DuckDuckGo search failed: %s", e)
        return None

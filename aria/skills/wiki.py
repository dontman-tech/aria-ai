"""Wikipedia skill - look up articles on Wikipedia."""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
import json
from typing import Optional

from aria.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


class WikiSkill(Skill):
    name = "wiki"
    description = "Look up Wikipedia articles"
    patterns = [
        r"\bwho (is|was|are|were)\b",
        r"\bwhat (is|was|are|were)\b",
        r"\bwikipedia\b",
        r"\btell me about\b",
    ]
    keywords = ["who is", "who was", "what is", "what was", "tell me about", "wikipedia"]

    def execute(self, text: str) -> SkillResult:
        query = self._extract_query(text)
        if not query:
            return SkillResult(success=False, message="What should I look up, Boss?")

        result = self._lookup(query)
        if result:
            return result
        return SkillResult(success=False, message=f"I couldn't find anything on '{query}', Boss.")

    def matches(self, text: str) -> bool:
        """Check if this skill matches, excluding self-referential questions."""
        lower = text.lower().strip()
        # Don't match questions directed at ARIA itself
        self_phrases = (
            "who are you", "what are you", "who is aria", "what is aria",
            "who is friday", "what is friday", "who is jarvis", "what is jarvis",
        )
        if any(lower.startswith(p) or lower == p for p in self_phrases):
            return False
        return super().matches(text)

    def _extract_query(self, text: str) -> str:
        lower = text.lower()
        for trigger in ("who is", "who was", "who are", "who were", "what is", "what was", "what are", "what were", "tell me about", "wikipedia", "look up"):
            if lower.startswith(trigger):
                return text[len(trigger):].strip().strip("?").strip()
        return ""

    def _lookup(self, query: str) -> Optional[SkillResult]:
        try:
            encoded = urllib.parse.quote(query.replace(" ", "_"))
            url = f"{WIKI_API}{encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "ARIA/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            extract = data.get("extract", "")
            title = data.get("title", query)
            if extract:
                # Trim to first 2 sentences for speech
                sentences = extract.split(". ")
                short = ". ".join(sentences[:2]) + "."
                return SkillResult(
                    success=True,
                    message=f"{title}: {short} Here's what I found, Boss.",
                    data={"title": title, "full_extract": extract, "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")},
                )
        except Exception as e:
            logger.debug("Wiki lookup failed: %s", e)
        return None

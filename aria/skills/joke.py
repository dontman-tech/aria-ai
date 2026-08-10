"""Joke skill - tells jokes to lighten the mood."""

from __future__ import annotations

import random

from aria.skills.base import Skill, SkillResult

JOKES = [
    "Why did the AI cross the road? To optimize the chicken's path, Boss.",
    "I told my computer I needed a break — now it won't stop sending me KitKat ads.",
    "How many programmers does it take to change a light bulb? None. That's a hardware problem.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I'd tell you a UDP joke, but you might not get it.",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "Why did the function return early? It had a breakpoint, Boss.",
    "A SQL query walks into a bar, sees two tables, and asks: 'Mind if I join you?'",
    "Debugging: being the detective in a crime movie where you're also the murderer.",
    "Why was the JavaScript developer sad? Because they didn't 'null' how to express their feelings.",
]


class JokeSkill(Skill):
    name = "joke"
    description = "Tell a joke"
    patterns = [
        r"\btell (me )?a joke\b",
        r"\bmake me laugh\b",
        r"\bsomething funny\b",
        r"\bjoke\b",
    ]
    keywords = ["joke", "funny", "make me laugh"]

    def execute(self, text: str) -> SkillResult:
        return SkillResult(success=True, message=random.choice(JOKES))

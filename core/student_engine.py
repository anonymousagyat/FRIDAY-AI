"""
JARVIS Student Reflexion Engine — Autonomous Continuous Learning.
Enables Friday to learn like a human student from Sir's feedback, corrections, and instructions.
Whenever Sir corrects a mistake or teaches a rule, Friday analyzes it, stores it in her
Student Notebook, and dynamically retrieves it so she never repeats mistakes.
"""

import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from .memory import memory_engine


class StudentEngine:
    """Autonomous Reflexion & Student Notebook Manager."""

    TEACHING_SIGNALS = [
        # English patterns
        r"\blearn\b", r"\brule\b", r"\bfrom now on\b", r"\bdon'?t say\b", r"\bstop saying\b",
        r"\bnever say\b", r"\binstead of\b", r"\byou should have\b", r"\byou should said\b",
        r"\bnot like that\b", r"\byou feel dumb\b", r"\bso dumb\b", r"\bwrong\b",
        r"\bmistake\b", r"\bremember this rule\b", r"\bteach\b", r"\bnote this down\b",
        # Hindi / Hinglish patterns
        r"\bseekh\b", r"\bseekho\b", r"\baage se\b", r"\baise mat\b", r"\baise nahi\b",
        r"\bmat bola\b", r"\bmat bolo\b", r"\bmat karo\b", r"\bgalat hai\b", r"\byaad rakhna\b",
        r"\brule bana\b", r"\bsamajh lo\b", r"\bdhyaan rakhna\b"
    ]

    EXTRACTION_PROMPT = """You are the Reflexion Engine for FRIDAY, an autonomous AI assistant whose mentor/teacher is Sir / Boss.
Your job is to analyze user feedback, corrections, or instructions and extract a structured student lesson so Friday learns and never makes that mistake again.

Analyze the user's input:
If Sir is teaching Friday a rule, correcting a mistake, giving feedback, or stating how he wants things done:
Return ONLY valid JSON:
{
    "is_lesson": true,
    "topic": "short snake_case topic name (e.g. media_titles, browser_choice, study_mode)",
    "trigger": "what user commands or situations trigger this rule",
    "mistake": "what Friday did wrong or must avoid doing",
    "rule": "the clear, actionable rule/behavior Friday must follow",
    "example": "concrete example of bad vs good behavior",
    "acknowledgment": "sweet, respectful Hinglish spoken acknowledgment to Sir (e.g. 'Ji Sir, maine apni notebook mein note kar liya hai ki...')"
}

If the user is NOT teaching, correcting, or setting a rule (just chatting, asking a question, or giving a standard command):
Return ONLY valid JSON:
{"is_lesson": false}
"""

    def __init__(self, ai_engine=None):
        self.ai_engine = ai_engine

    def set_ai_engine(self, ai_engine):
        self.ai_engine = ai_engine

    def should_reflect(self, text: str) -> bool:
        """Fast regex heuristic check to detect if input contains teaching/correction signals."""
        if not text:
            return False
        clean = text.lower().strip()
        for pat in self.TEACHING_SIGNALS:
            if re.search(pat, clean):
                return True
        return False

    def reflect_and_learn(self, user_text: str, prior_assistant_response: str = None) -> Optional[Dict[str, Any]]:
        """
        Analyze user input for student lessons.
        If a lesson is found, saves it to the student notebook in memory and returns the lesson dict.
        """
        if not self.should_reflect(user_text) and not self._contains_strong_correction(user_text):
            return None

        if not self.ai_engine:
            return None

        prompt = f"""{self.EXTRACTION_PROMPT}

CONTEXT:
{f"FRIDAY'S PRIOR RESPONSE: '{prior_assistant_response}'" if prior_assistant_response else ""}
SIR'S INPUT: "{user_text}"
"""
        try:
            # Quick call using Groq or Gemini
            res_json = None
            if getattr(self.ai_engine, 'groq_client', None):
                for m in ['openai/gpt-oss-20b', 'qwen/qwen3.8-27b', 'groq/compound-mini']:
                    try:
                        comp = self.ai_engine.groq_client.chat.completions.create(
                            model=m,
                            messages=[{"role": "user", "content": prompt}],
                            response_format={"type": "json_object"},
                            temperature=0.2,
                            max_tokens=600
                        )
                        raw = comp.choices[0].message.content
                        res_json = json.loads(raw)
                        break
                    except Exception:
                        continue

            if not res_json and getattr(self.ai_engine, 'modern_client', None):
                try:
                    res = self.ai_engine.modern_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt
                    )
                    res_json = self.ai_engine._extract_json(res.text)
                except Exception:
                    pass

            if res_json and res_json.get("is_lesson"):
                topic = res_json.get("topic") or "general_behavior"
                trigger = res_json.get("trigger") or "general"
                rule = res_json.get("rule") or ""
                mistake = res_json.get("mistake") or ""
                example = res_json.get("example") or ""

                if rule:
                    saved = memory_engine.add_lesson(
                        topic=topic,
                        trigger=trigger,
                        rule=rule,
                        mistake=mistake,
                        example=example
                    )
                    res_json["saved"] = saved
                    print(f"[StudentEngine] Learned lesson from Sir: [{topic}] {rule}")
                    return res_json

        except Exception as e:
            print(f"[StudentEngine] Reflexion error: {e}")

        return None

    def _contains_strong_correction(self, text: str) -> bool:
        t = text.lower()
        return ("he should" in t or "she should" in t or "you should" in t or
                "don't" in t or "dont" in t or "dumb" in t or "wrong" in t)

    def learn_rule_direct(self, topic: str, trigger: str, rule: str,
                          mistake: str = "", example: str = "") -> Dict[str, Any]:
        """Direct programmatic learning (e.g. from tool execution)."""
        return memory_engine.add_lesson(topic, trigger, rule, mistake, example)

    def get_lessons(self, query: str = "") -> List[Dict[str, Any]]:
        """Get all learned lessons or filter."""
        return memory_engine.get_lessons(query)

    def delete_lesson(self, topic_or_id: str) -> Dict[str, Any]:
        """Remove a lesson from the student notebook."""
        return memory_engine.delete_lesson(topic_or_id)

    def get_lessons_prompt(self, command: str = "") -> str:
        """Get the formatted student notebook prompt block."""
        return memory_engine.get_lessons_prompt(command)


# Singleton instance
student_engine = StudentEngine()

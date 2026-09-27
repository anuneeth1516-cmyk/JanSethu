import json
import os
import re
from typing import Any, Protocol

import httpx


class AIService(Protocol):
    async def analyze_problem(self, title: str, description: str, location: str = "", image_name: str | None = None) -> dict[str, Any]: ...
    async def chat(self, message: str) -> str: ...
    async def test_connection(self) -> dict[str, Any]: ...


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _validated_analysis(data: dict[str, Any]) -> dict[str, Any]:
    from app.schemas.auth import ProblemAnalysis

    return ProblemAnalysis.model_validate(data).model_dump()


class GeminiService:
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    async def test_connection(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": self.api_key},
                )
                if res.status_code == 200:
                    return {"status": "connected", "model": self.model, "provider": "gemini"}
                return {"status": "error", "error": f"API returned status {res.status_code}"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def analyze_problem(self, title: str, description: str, location: str = "", image_name: str | None = None) -> dict[str, Any]:
        prompt = (
            "Analyze this civic problem report. Return ONLY a JSON object with exactly these fields:\n"
            "- summary: concise factual summary of the problem\n"
            "- severity: one of High, Medium, Low\n"
            "- urgency: one of Immediate, Soon, Planned\n"
            "- required_skills: 3-6 specific skills needed to solve it\n"
            "- required_expertise: 2-5 subject areas or disciplines needed\n"
            "- required_resources: 2-5 physical, organizational, or technical resources needed\n"
            "- tags: 3-6 concise searchable tags\n\n"
            f"Problem title: {title}\n"
            f"Civic problem description: {description}\n"
            f"Problem location: {location or 'Not provided'}\n"
            + (f"Evidence file attached: {image_name}\n" if image_name else "")
        )
        try:
            result = await self._generate(prompt, json_mode=True)
            cleaned = _clean_json_text(result)
            return _validated_analysis(json.loads(cleaned))
        except Exception as exc:
            fallback = LocalDemoAIService().analyze_problem_sync(title, description, location, image_name)
            fallback["ai_error"] = str(exc)[:160]
            return fallback

    async def chat(self, message: str) -> str:
        prompt = (
            "You are jansethu's civic collaboration AI guide. jansethu connects citizens with university researchers and industry partners to solve real local problems.\n"
            "Help the user understand how to report a problem, what evidence is helpful, how AI identifies needs, and how university and industry partners collaborate.\n"
            "Be encouraging, concise, actionable, and warm. User message: " + message
        )
        try:
            return await self._generate(prompt)
        except Exception as exc:
            return (
                "I'm jansethu's civic collaboration assistant. You can report problems like road damage, waterlogging, or waste issues. "
                "Our AI automatically identifies required capabilities (such as GIS, drainage engineering, or sensor tech) and matches you with university and industry teams."
            )

    async def _generate(self, prompt: str, json_mode: bool = False) -> str:
        generation_config: dict[str, Any] = {"temperature": 0.3}
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "systemInstruction": {
                        "parts": [{"text": "You are jansethu's civic problem intelligence analyst and collaboration bridge engine."}]
                    },
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": generation_config,
                },
            )
            response.raise_for_status()
            candidates = response.json().get("candidates", [])
            if not candidates:
                raise ValueError("No response generated from Gemini")
            return candidates[0]["content"]["parts"][0]["text"]

class LocalDemoAIService:
    async def test_connection(self) -> dict[str, Any]:
        return {"status": "demo", "model": "local_heuristics", "provider": "demo"}

    async def analyze_problem(self, title: str, description: str, location: str = "", image_name: str | None = None) -> dict[str, Any]:
        return self.analyze_problem_sync(title, description, location, image_name)

    def analyze_problem_sync(self, title: str, description: str, location: str = "", image_name: str | None = None) -> dict[str, Any]:
        text = f"{title} {description} {location}".lower()
        if any(word in text for word in ("plastic", "waste", "recycling", "garbage")):
            skills = ["Waste systems design", "Recycling operations", "Community education"]
            expertise = ["Circular economy", "Solid waste management"]
            resources = ["Segregation bins", "Recycling partner network", "Waste audit equipment"]
            tags = ["plastic waste", "recycling", "waste management"]
            severity, urgency = "High", "Soon"
        elif any(word in text for word in ("pothole", "road", "traffic", "accident", "drainage")):
            skills = ["Road engineering", "Traffic safety assessment", "Municipal coordination"]
            expertise = ["Civil infrastructure", "Road safety"]
            resources = ["Road inspection equipment", "Traffic control materials", "Repair contractor"]
            tags = ["pothole", "road safety", "traffic"]
            severity, urgency = "High", "Immediate"
        else:
            skills = ["Community assessment", "Field research", "Local implementation"]
            expertise = ["Civic problem solving", "Community engagement"]
            resources = ["Field survey equipment", "Local coordination"]
            tags = ["community", "field research", "civic improvement"]
            severity, urgency = "Medium", "Soon"
        return _validated_analysis(
            {
                "summary": f"{title.strip()}: {description.strip()[:130]}",
                "severity": severity,
                "urgency": urgency,
                "required_skills": skills,
                "required_expertise": expertise,
                "required_resources": resources,
                "tags": tags,
            }
        )

    async def chat(self, message: str) -> str:
        words = message.lower()
        if "report" in words or "problem" in words:
            return "Start with what is happening, where it is happening, who is affected, and any photo or video evidence. Open 'Report a problem' and submit those details; jansethu will identify the needed capabilities and return potential collaborators."
        if "match" in words or "collaborat" in words or "university" in words or "industry" in words:
            return "After analysis, jansethu ranks potential collaborators by relevance, including research skills, technical equipment, and corporate CSR resources. Universities contribute technical frameworks while industry partners contribute prototyping materials."
        if "safe" in words or "urgent" in words or "danger" in words:
            return "Mark urgent safety risks clearly in your description, explain who may be harmed, and include the location. The AI analysis uses that context to estimate urgency and notify relevant stakeholders."
        return "I can help you report a problem, explore AI analysis, or find collaborators. What would you like to know?"


def create_ai_service(api_key: str | None = None, model: str | None = None) -> AIService:
    key = (api_key or os.getenv("AI_API_KEY", "")).strip()
    selected_model = model or os.getenv("AI_MODEL", "gemini-3.5-flash")
    if key:
        return GeminiService(key, selected_model)
    return LocalDemoAIService()
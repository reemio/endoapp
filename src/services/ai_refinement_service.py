import json
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


@dataclass
class RefinementRequest:
    findings_draft: str
    conclusions_draft: str = ""
    recommendations_draft: str = ""
    patient_context: Dict[str, Any] = field(default_factory=dict)
    user_instruction: str = ""
    brevity_mode: bool = True


@dataclass
class RefinementResponse:
    findings_text: str
    conclusions: List[str]
    recommendations: List[str]
    raw_response: str = ""
    model_used: str = "fallback"
    usage: Dict[str, Any] = field(default_factory=dict)


REPORTING_RULES = textwrap.dedent(
    """
    STRUCTURE:
      1. OGD Report (single paragraph). Describe scope extent, esophagus, stomach (body, antrum, pylorus), duodenum, then retroflexion. Use precise GI descriptors (erythematous, ulcerated, contact bleeding, fibrin deposition, Hill Grade, Forrest classification). No bullet points.
      2. Conclusions (numbered 1., 2., …). Keep concise yet complete. End with “Otherwise normal OGD up to D2.” when appropriate.
      3. Recommendations (brevity style). Provide short numbered items ordered by: PPI/H2 blocker → mucosal protectant (sucralfate/bismuth) → antimicrobials (H. pylori) → prokinetic/antispasmodic → antacid/reflux support → diet/lifestyle → follow-up. Always include drug, dose, frequency, and duration.

    STYLE:
      • Voice objective and clinical; tense past or present perfect.
      • Use metric units and standard GI abbreviations (D1, D2, GEFV, LA Grade, Forrest).
      • Retroflexion sentence begins with “On retroflexion…”.
      • State “Competent/non-closing GEFV Hill Grade X” exactly when describing GEFV.

    MEDICATION RULES (default unless user overrides):
      • PPI: Rabeprazole 20 mg bd × 8–12 weeks preferred (or Esomeprazole 40 mg bd).
      • H. pylori triple therapy: Rabeprazole 20 mg bd + Amoxicillin 1 g bd + Clarithromycin 500 mg bd × 14 days.
      • Quadruple second line: Rabeprazole 20 mg bd + Bismuth 524 mg qid + Tetracycline 500 mg qid + Metronidazole 400 mg tds × 14 days.
      • Sucralfate 1 g qid × 4 weeks.
      • Itopride 50 mg tds × 6 weeks.
      • Buscopan 10–20 mg tds PRN; Paracetamol for analgesia if needed.
      • Gaviscon 20 ml after meals & hs for reflux.
      • Ursodeoxycholic acid 300 mg bd × 6 weeks for bile reflux.
      • For bleeding ulcers: add Bismuth, avoid NSAIDs, monitor Hb.
    """
).strip()


class AIRefinementService:
    OPENAI_MODEL_DEFAULT = "gpt-4.1"
    OPENAI_MODEL_CHOICES = [
        "gpt-5",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4.1-mini",
        "gpt-4o-mini",
        "o4-mini",
        "gpt-4.1-distill",
        "gpt-3.5-turbo",
    ]

    def __init__(self, settings_manager=None, error_handler=None):
        self.logger = logging.getLogger("AIRefinementService")
        self.settings_manager = settings_manager
        self.error_handler = error_handler
        self._load_settings()

    def _load_settings(self):
        defaults = {
            "provider": "openai",
            "model": self.OPENAI_MODEL_DEFAULT,
            "temperature": 0.2,
            "max_tokens": 900,
            "api_key_env": "OPENAI_API_KEY",
            "enabled": True,
            "brevity_default": True,
            "stored_api_key": "",
        }
        if self.settings_manager:
            ai_settings = self.settings_manager.get("ai_refinement", default={}) or {}
            merged = defaults | ai_settings
        else:
            merged = defaults
        self.provider = merged["provider"]
        self.model = self._normalize_model(merged.get("model"))
        self.temperature = merged["temperature"]
        self.max_tokens = merged["max_tokens"]
        self.api_key_env = merged["api_key_env"]
        self.enabled = merged["enabled"]
        self.default_brevity = merged["brevity_default"]
        self.stored_api_key = (merged.get("stored_api_key") or "").strip()
        self.logger.info(
            "AIRefinementService configured (provider=%s, model=%s, enabled=%s)",
            self.provider,
            self.model,
            self.enabled,
        )

    def refresh_settings(self):
        self._load_settings()

    def _normalize_model(self, raw_model):
        model = (raw_model or "").strip()
        if self.provider == "openai" and model not in self.OPENAI_MODEL_CHOICES:
            if model:
                self.logger.warning(
                    "Unknown OpenAI model '%s'; defaulting to %s",
                    model,
                    self.OPENAI_MODEL_DEFAULT,
                )
            model = self.OPENAI_MODEL_DEFAULT
            if self.settings_manager:
                self.settings_manager.set("ai_refinement", "model", value=model)
        return model or self.OPENAI_MODEL_DEFAULT

    def get_environment_issues(self) -> List[str]:
        issues = []
        if self.provider == "openai":
            api_key_present = bool(os.getenv(self.api_key_env) or self.stored_api_key)
            if not api_key_present:
                issues.append(
                    f"API key missing. Set environment variable {self.api_key_env} or store a key via File → Settings."
                )
        return issues

    def refine(self, request: RefinementRequest, conversation_history: Optional[List[Dict[str, str]]] = None) -> RefinementResponse:
        if not self.enabled:
            raise RuntimeError("AI refinement is disabled in settings.")

        readiness_issues = self.get_environment_issues()
        if readiness_issues:
            raise RuntimeError(" ".join(readiness_issues))

        conversation_history = conversation_history or []
        if self.provider != "openai":
            return self._fallback_refinement(request)

        try:
            response = self._call_openai_chat(request, conversation_history)
            if response:
                return response
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("LLM refinement failed, falling back to formatter: %s", exc, exc_info=True)
            if self.error_handler:
                self.error_handler.log_warning(f"AI refinement failed: {exc}")
        return self._fallback_refinement(request)

    def _call_openai_chat(self, request: RefinementRequest, history: List[Dict[str, str]]) -> Optional[RefinementResponse]:
        api_key = os.getenv(self.api_key_env) or self.stored_api_key
        if not api_key:
            raise RuntimeError(f"Set {self.api_key_env} or store an API key first.")

        messages = [{"role": "system", "content": self._system_prompt(request.brevity_mode)}]
        messages.extend(history)
        messages.append({"role": "user", "content": self._build_user_prompt(request)})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": float(self.temperature),
            "max_tokens": int(self.max_tokens),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI API returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        parsed = self._parse_ai_payload(content)
        usage = data.get("usage") or {}
        return RefinementResponse(
            findings_text=parsed["findings"],
            conclusions=parsed["conclusions"],
            recommendations=parsed["recommendations"],
            raw_response=content,
            model_used=self.model,
            usage=usage,
        )

    def _system_prompt(self, brevity: bool) -> str:
        brevity_text = "Keep each recommendation under 20 words." if brevity else ""
        return textwrap.dedent(
            f"""
            You are an expert gastroenterology reporting assistant.
            Produce output strictly following the rules below:
            {REPORTING_RULES}

            OUTPUT FORMAT:
            {{
              "findings": "<OGD paragraph>",
              "conclusions": ["1. …", "2. …"],
              "recommendations": ["…"]
            }}

            {brevity_text}
            """
        ).strip()

    def _build_user_prompt(self, request: RefinementRequest) -> str:
        patient_lines = []
        patient_ctx = request.patient_context or {}
        for key in ("name", "patient_id", "age", "gender", "indication", "report_title"):
            val = patient_ctx.get(key) or patient_ctx.get("patient_info", {}).get(key)
            if val:
                patient_lines.append(f"{key.replace('_', ' ').title()}: {val}")
        context_text = "\n".join(patient_lines).strip()
        return textwrap.dedent(
            f"""
            PATIENT CONTEXT:
            {context_text or 'Not provided'}

            ROUGH FINDINGS:
            {request.findings_draft.strip() or 'None'}

            ROUGH CONCLUSIONS:
            {request.conclusions_draft.strip() or 'None'}

            ROUGH RECOMMENDATIONS:
            {request.recommendations_draft.strip() or 'None'}

            USER INSTRUCTION:
            {request.user_instruction.strip() or 'Polish professionally.'}
            """
        ).strip()

    def _parse_ai_payload(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(self._extract_json(content))
        except json.JSONDecodeError:
            return {
                "findings": content.strip(),
                "conclusions": self._extract_numbered_lines(content),
                "recommendations": [],
            }

    def _extract_json(self, text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text

    def _extract_numbered_lines(self, text: str) -> List[str]:
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if re.match(r"^\d+\.", line):
                lines.append(line)
        return lines

    def _fallback_refinement(self, request: RefinementRequest) -> RefinementResponse:
        def to_paragraph(src: str) -> str:
            cleaned = " ".join(token.strip() for token in src.splitlines() if token.strip())
            return cleaned.capitalize()

        def to_numbered(src: str, prefix: str) -> List[str]:
            parts = [p.strip(" .") for p in src.splitlines() if p.strip()]
            if not parts:
                return [f"{prefix} pending clinical correlation."]
            return [f"{idx + 1}. {part.capitalize()}" for idx, part in enumerate(parts)]

        findings_text = to_paragraph(request.findings_draft or "Normal study.")
        conclusions = to_numbered(request.conclusions_draft or "Post-procedural review recommended.", "Conclusion")
        recommendations = to_numbered(
            request.recommendations_draft or "Follow up with referring clinician as scheduled.",
            "Recommendation",
        )
        return RefinementResponse(
            findings_text=findings_text,
            conclusions=conclusions,
            recommendations=recommendations,
            raw_response=findings_text,
            model_used="fallback-formatter",
        )

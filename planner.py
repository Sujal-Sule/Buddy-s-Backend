import json
import logging
import os
from fallback_planner import build_explain_primitives, build_fallback_plan
from models import NextAction, PlanRequest, PlanResponse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore

logger = logging.getLogger("TheBuddyPlanner")
DEFAULT_MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = (
    "You are JARVIS / The Buddy, an Autonomous Android OS Agent and Visual Tutor.\n"
    "Operate in a closed-loop Perceive -> Reason -> Act -> Verify cycle. Return ONLY valid JSON matching PlanResponse:\n"
    '{"status":"ok","mode":"ACTION"|"CONVERSATION"|"EXPLAIN","speech_reply":"...","emotional_context":"warm"|"calm_analytical"|"cautious"|"enthusiastic",'
    '"next_action":{"action_type":"LAUNCH_APP"|"CLICK_NODE"|"TYPE_TEXT"|"SCROLL"|"BACK"|"GLOBAL_HOME"|"SPOTLIGHT_GUIDE"|"SCREENSHOT"|"DONE",'
    '"target":"...","payload":null,"draft_content":null,"instruction":null,"requires_confirmation":false},'
    '"scene_title":"","scene_summary":"","canvas_scene":null}\n'
    "Rules:\n"
    "1. Return EXACTLY ONE next_action per call based on current_ui_tree and history.\n"
    "2. Never guess hardcoded apps; pick package_name ONLY from installed_apps.\n"
    "3. Set requires_confirmation=true for sending messages, posting on social media, payments, or deleting items.\n"
    "4. For guided multi-stage writing/editing (bios, lyrics, forms), use SPOTLIGHT_GUIDE with draft_content and instruction.\n"
    "5. For conceptual explanations, set mode='EXPLAIN', next_action.action_type='DONE', and populate canvas_scene with 6-10 vector primitives (box, arrow, label, highlight)."
)


class TaskPlanner:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        valid = bool(api_key) and api_key != "your_gemini_api_key_here" and genai is not None
        self.client = genai.Client(api_key=api_key) if valid else None

    def plan_next(self, req: PlanRequest) -> PlanResponse:
        if self.client and types is not None:
            apps_ctx = [f"{a.app_name}:{a.package_name}" for a in req.installed_apps[:80]]
            ui_ctx = [
                f"{n.node_id}|{n.class_name}|txt={n.text}|desc={n.content_description}|clk={n.is_clickable}|edt={n.is_editable}|{n.bounds_in_screen}"
                for n in req.current_ui_tree[:35]
            ]
            contents = (
                f"Prompt: {req.user_prompt}\nModeHint: {req.mode}\nActivePkg: {req.active_package}\n"
                f"History: {req.history[-6:]}\nInstalledApps: {apps_ctx}\nUITree: {ui_ctx}"
            )
            for model_id in (self.model_name, "gemini-2.5-flash-lite"):
                try:
                    cfg_args: dict = {
                        "system_instruction": SYSTEM_PROMPT,
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    }
                    if getattr(types, "ThinkingConfig", None):
                        cfg_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                    resp = self.client.models.generate_content(
                        model=model_id, contents=contents, config=types.GenerateContentConfig(**cfg_args)
                    )
                    raw = (resp.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = PlanResponse.model_validate(json.loads(raw))
                    return self._post_validate(parsed, req)
                except Exception as exc:
                    logger.warning("Planner model %s fallback (%s)", model_id, exc)
        return build_fallback_plan(req)

    def _post_validate(self, parsed: PlanResponse, req: PlanRequest) -> PlanResponse:
        if parsed.mode == "EXPLAIN" and (not parsed.canvas_scene):
            title, summary, scene = build_explain_primitives(req.user_prompt)
            return parsed.model_copy(update={"scene_title": title, "scene_summary": summary, "canvas_scene": scene, "next_action": NextAction(action_type="DONE")})
        return parsed


planner = TaskPlanner()

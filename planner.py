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
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are The Buddy, an Autonomous Android OS Agent & Visual Co-Pilot.\n"
    "Return ONLY valid JSON matching PlanResponse:\n"
    '{"status":"ok","mode":"ACTION"|"CONVERSATION"|"EXPLAIN"|"SCREEN_READ"|"FORM_FILL","speech_reply":"...",'
    '"emotional_context":"warm"|"calm_analytical"|"cautious"|"enthusiastic",'
    '"next_action":{"action_type":"FORM_FILL"|"MEDIA_SHARE"|"SCREEN_READ"|"NAVIGATE"|"CANVAS_EXPLAIN"|'
    '"LAUNCH_APP"|"CLICK_NODE"|"TYPE_TEXT"|"SCROLL"|"BACK"|"GLOBAL_HOME"|"SPOTLIGHT_GUIDE"|"SCREENSHOT"|"SYSTEM_INTENT"|"DONE",'
    '"target":"...","payload":null,"draft_content":null,"instruction":null,"requires_confirmation":false},'
    '"scene_title":"","scene_summary":"","canvas_scene":null,"summary_bullets":null,"translated_text":""}\n'
    "Rules:\n"
    "1. Creative, conversational, advice, coding, or knowledge requests -> mode='CONVERSATION', action_type='DONE', give a direct helpful speech_reply (never 'All caught up').\n"
    "2. Multi-step app tasks (e.g. 'open WhatsApp and open R.S.S group', 'play X on Spotify'): Step 1 LAUNCH_APP from InstalledApps; next cycles examine UITree, CLICK_NODE matching row (skip nav tabs/search hints), or CLICK_NODE Search -> TYPE_TEXT -> CLICK_NODE result -> SCROLL DOWN if absent. Only return DONE after completing the subgoal.\n"
    "3. Form auto-fill -> FORM_FILL. Media search/share/cleanup -> MEDIA_SHARE. Summarize/translate -> mode='SCREEN_READ', action_type='SCREEN_READ'.\n"
    "4. Explanations -> mode='EXPLAIN', action_type='CANVAS_EXPLAIN', populate canvas_scene on 0..1000 grid.\n"
    "5. Set requires_confirmation=true before sending external messages, posting, payments, or file deletion."
)


class TaskPlanner:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        valid = bool(api_key) and api_key != "your_gemini_api_key_here" and genai is not None
        self.client = genai.Client(api_key=api_key) if valid else None

    def plan_next(self, req: PlanRequest) -> PlanResponse:
        try:
            if self.client and types is not None:
                apps_ctx = [f"{a.app_name}:{a.package_name}" for a in req.installed_apps[:90]]
                ui_ctx = [
                    f"{n.node_id}|{n.class_name}|txt={n.text}|desc={n.content_description}|clk={n.is_clickable}|edt={n.is_editable}|{n.bounds_in_screen}"
                    for n in req.current_ui_tree[:60]
                ]
                contents = (
                    f"Prompt: {req.user_prompt}\nModeHint: {req.mode}\nActivePkg: {req.active_package}\n"
                    f"History: {req.history[-8:]}\nInstalledApps: {apps_ctx}\nUITree: {ui_ctx}"
                )
                models = tuple(dict.fromkeys((self.model_name, "gemini-2.5-flash", "gemini-2.5-flash-lite")))
                for model_id in models:
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
        except Exception as outer:
            logger.error("Unexpected planner failure recovered: %s", outer)
        return build_fallback_plan(req)

    def _post_validate(self, parsed: PlanResponse, req: PlanRequest) -> PlanResponse:
        if (parsed.mode == "EXPLAIN" or parsed.next_action.action_type == "CANVAS_EXPLAIN") and (not parsed.canvas_scene):
            title, summary, scene = build_explain_primitives(req.user_prompt)
            return parsed.model_copy(update={
                "mode": "EXPLAIN",
                "scene_title": title,
                "scene_summary": summary,
                "canvas_scene": scene,
                "next_action": NextAction(action_type="CANVAS_EXPLAIN"),
            })
        return parsed


planner = TaskPlanner()


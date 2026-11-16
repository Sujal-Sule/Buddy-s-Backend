import base64
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
    "You are The Buddy, an Autonomous Android OS Agent & Universal Technical Illustrator.\n"
    "Return ONLY valid JSON matching PlanResponse:\n"
    '{"status":"ok","mode":"ACTION"|"CONVERSATION"|"EXPLAIN"|"SCREEN_READ"|"FORM_FILL","speech_reply":"...",'
    '"emotional_context":"warm"|"calm_analytical"|"cautious"|"enthusiastic",'
    '"next_action":{"action_type":"FORM_FILL"|"MEDIA_SHARE"|"SCREEN_READ"|"NAVIGATE"|"CANVAS_EXPLAIN"|'
    '"LAUNCH_APP"|"CLICK_NODE"|"TYPE_TEXT"|"SCROLL"|"BACK"|"GLOBAL_HOME"|"SPOTLIGHT_GUIDE"|"SCREENSHOT"|"SYSTEM_INTENT"|"DONE",'
    '"target":"...","payload":null,"draft_content":null,"instruction":null,"requires_confirmation":false},'
    '"scene_title":"","scene_summary":"","canvas_scene":null,"summary_bullets":null,"translated_text":""}\n'
    "Rules:\n"
    "1. Creative, conversational, advice, coding, or knowledge -> mode='CONVERSATION', action_type='DONE', helpful speech_reply.\n"
    "2. Multi-step app tasks: LAUNCH_APP -> inspect UITree -> CLICK_NODE matching row (skip nav tabs/search hints) -> TYPE_TEXT -> SCROLL.\n"
    "3. Form auto-fill -> FORM_FILL. Media -> MEDIA_SHARE. Summarize/translate -> SCREEN_READ.\n"
    "4. Universal Generative Vector Engine when mode='EXPLAIN' (action_type='CANVAS_EXPLAIN'):\n"
    "   Analyze the user's concept first across ANY domain (mechanics, biology, software, electronics, physics, finance). Identify real components, spatial relationships, and motion/flow behaviors, then compose 6 to 15 primitives on a 0..1000 grid across step_index 1..4:\n"
    "   - 'svg_path': {d:'M ... C ... Z', strokeColor, fillColor, strokeWidth, label} for any custom silhouette, organ, circuit, frame, container, or icon.\n"
    "   - 'procedural_polygon' / 'radial_array': {cx, cy, sides, innerRadius, outerRadius, angularVelocity, direction:'CW'|'CCW', color, label} for rotating teeth, spokes, turbines, cells, atoms, or wheels.\n"
    "   - 'flow_spline': {startX, startY, cp1X, cp1Y, cp2X, cp2Y, endX, endY, particleColor, animatedFlow:true, particleCount, flowSpeed} for electricity, blood flow, torque, network packets, or cash flow.\n"
    "   - 'state_morph': {x, y, width, height, d, axis:'X'|'Y'|'SCALE'|'OPACITY', amplitude, frequency, phaseOffset, color, label} for oscillating pistons, valves, waves, pulses, or buffers.\n"
    "   - 'callout_tag': {x, y, title, subtitle, targetX, targetY, color} for leader-line annotations anchored to elements.\n"
    "5. Direct OS intents -> SYSTEM_INTENT. Set requires_confirmation=true before sending/posting/paying/deleting.\n"
    "6. If screenshot attached, describe visually or return CLICK_NODE with target='norm_x,norm_y' in 0..1."
)


class TaskPlanner:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        valid = bool(api_key) and api_key != "your_gemini_api_key_here" and genai is not None
        self.client = genai.Client(api_key=api_key) if valid else None

    def _build_contents(self, req: PlanRequest):
        apps_ctx = [f"{a.app_name}:{a.package_name}" for a in req.installed_apps[:90]]
        ui_ctx = [
            f"{n.node_id}|{n.class_name}|txt={n.text}|desc={n.content_description}|clk={n.is_clickable}|edt={n.is_editable}|{n.bounds_in_screen}"
            for n in req.current_ui_tree[:60]
        ]
        text_part = (
            f"Prompt: {req.user_prompt}\nModeHint: {req.mode}\nActivePkg: {req.active_package}\n"
            f"History: {req.history[-10:]}\nInstalledApps: {apps_ctx}\nUITree: {ui_ctx}"
        )
        if req.screen_image_base64 and types is not None:
            try:
                raw_bytes = base64.b64decode(req.screen_image_base64, validate=False)
                if len(raw_bytes) > 64:
                    return [text_part, types.Part.from_bytes(data=raw_bytes, mime_type="image/jpeg")]
            except Exception as exc:
                logger.warning("Ignoring invalid screen snapshot (%s)", exc)
        return text_part

    def plan_next(self, req: PlanRequest) -> PlanResponse:
        try:
            if self.client and types is not None:
                contents = self._build_contents(req)
                models = tuple(dict.fromkeys((self.model_name, "gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash")))
                for model_id in models:
                    try:
                        cfg_args: dict = {
                            "system_instruction": SYSTEM_PROMPT,
                            "response_mime_type": "application/json",
                            "response_schema": PlanResponse,
                            "max_output_tokens": 2048,
                            "temperature": 0.15,
                        }
                        if getattr(types, "ThinkingConfig", None):
                            cfg_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                        resp = self.client.models.generate_content(model=model_id, contents=contents, config=types.GenerateContentConfig(**cfg_args))
                        raw = (resp.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        return self._post_validate(PlanResponse.model_validate(json.loads(raw)), req)
                    except Exception as exc:
                        logger.warning("Planner model %s fallback (%s)", model_id, exc)
        except Exception as outer:
            logger.error("Unexpected planner failure recovered: %s", outer)
        return build_fallback_plan(req)

    def _post_validate(self, parsed: PlanResponse, req: PlanRequest) -> PlanResponse:
        if (parsed.mode == "EXPLAIN" or parsed.next_action.action_type == "CANVAS_EXPLAIN") and (not parsed.canvas_scene):
            title, summary, scene = build_explain_primitives(req.user_prompt)
            return parsed.model_copy(update={
                "mode": "EXPLAIN", "scene_title": title, "scene_summary": summary,
                "canvas_scene": scene, "next_action": NextAction(action_type="CANVAS_EXPLAIN"),
            })
        return parsed


planner = TaskPlanner()


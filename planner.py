import base64
import json
import logging
import os
from fallback_planner import build_fallback_plan
from intent_helpers import extract_explain_title
from models import NextAction, PlanRequest, PlanResponse, VectorPrimitive

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
_COORD_KEYS = ("cx", "cy", "x", "y", "width", "height", "targetX", "targetY", "startX", "startY", "cp1X", "cp1Y", "cp2X", "cp2Y", "endX", "endY", "innerRadius", "outerRadius")
_TYPE_ALIAS = {"procedural_polygon": "radial_array", "gear": "radial_array", "flow_curve": "flow_spline", "callout_label": "callout_tag"}
_ALLOWED_KEYS = set(VectorPrimitive.model_fields.keys())

SYSTEM_PROMPT = (
    "You are The Buddy, an Autonomous Android OS Agent & Technical Vector Illustrator.\n"
    "Return ONLY valid JSON matching PlanResponse:\n"
    '{"status":"ok","mode":"ACTION"|"CONVERSATION"|"EXPLAIN"|"SCREEN_READ"|"FORM_FILL","speech_reply":"...",'
    '"emotional_context":"warm"|"calm_analytical"|"cautious"|"enthusiastic",'
    '"next_action":{"action_type":"FORM_FILL"|"MEDIA_SHARE"|"SCREEN_READ"|"NAVIGATE"|"CANVAS_EXPLAIN"|'
    '"LAUNCH_APP"|"CLICK_NODE"|"TYPE_TEXT"|"SCROLL"|"BACK"|"GLOBAL_HOME"|"SPOTLIGHT_GUIDE"|"SCREENSHOT"|"SYSTEM_INTENT"|"DONE",'
    '"target":"...","payload":null,"draft_content":null,"instruction":null,"requires_confirmation":false},'
    '"scene_title":"","scene_summary":"","primitives":null,"summary_bullets":null,"translated_text":""}\n'
    "Rules:\n"
    "1. Creative, chat, advice, coding, or knowledge -> mode='CONVERSATION', action_type='DONE', concise speech_reply.\n"
    "2. Multi-step app tasks: LAUNCH_APP -> inspect UITree -> CLICK_NODE row (skip tabs/search hints) -> TYPE_TEXT -> SCROLL.\n"
    "3. Form auto-fill -> FORM_FILL. Media -> MEDIA_SHARE. Summarize/translate -> SCREEN_READ.\n"
    "4. BESPOKE VISUAL SCENE MANDATE when mode='EXPLAIN' (action_type='CANVAS_EXPLAIN'):\n"
    "   Compose a COMPLETELY UNIQUE, domain-accurate 2D illustration from scratch (6..14 primitives on 0..1000 grid, step_index 1..4).\n"
    "   NEVER reuse a generic template, boxes, or gears for non-mechanical subjects (use organs/membranes/chambers/circuits/prisms/waves instead).\n"
    "   - 'svg_path': bespoke curves/silhouettes (hearts, leaves, silicon dies, lenses, buildings, molecules) via d:'M ... C ... Z'.\n"
    "   - 'radial_array': orbiting satellites/ions/nodes (set innerRadius>=0.9*outerRadius for clean rings, or <0.85*outerRadius for teeth ONLY on mechanical topics).\n"
    "   - 'flow_spline': animated Bezier particle emitters for blood, electrons, light rays, packets, or forces.\n"
    "   - 'state_morph': axis 'WAVE' (sinusoidal waves), 'X'|'Y' (oscillation), 'SCALE' (pumping/breathing), 'OPACITY' (activation pulse).\n"
    "   - 'callout_tag': clean leader-line labels anchored to moving parts.\n"
    "5. CONTEXT AWARENESS: Use ActivePkg and ActiveActivity (from AccessibilityService) to provide screen-specific explanations and precise UI actions for the user's current screen.\n"
    "6. Direct OS intents -> SYSTEM_INTENT. Set requires_confirmation=true before sending/posting/paying/deleting."
)


def _sanitize_raw_plan(data: dict) -> dict:
    for key in ("primitives", "canvas_scene"):
        items = data.get(key)
        if not isinstance(items, list):
            continue
        cleaned = []
        for raw_p in items:
            if not isinstance(raw_p, dict):
                continue
            p = {k: v for k, v in raw_p.items() if k in _ALLOWED_KEYS}
            p["type"] = _TYPE_ALIAS.get(str(p.get("type", "")).lower(), p.get("type", "svg_path"))
            for ck in _COORD_KEYS:
                if ck in p and isinstance(p[ck], (int, float)):
                    p[ck] = max(0.0, min(1000.0, float(p[ck])))
            if p.get("type") == "radial_array":
                r_out = max(12.0, float(p.get("outerRadius", 72.0)))
                p["outerRadius"], p["innerRadius"] = r_out, min(r_out, max(4.0, float(p.get("innerRadius", r_out * 0.9))))
            cleaned.append(p)
        data[key] = cleaned
    return data


class TaskPlanner:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        valid = bool(api_key) and api_key != "your_gemini_api_key_here" and genai is not None
        self.client = genai.Client(api_key=api_key) if valid else None

    def _build_contents(self, req: PlanRequest):
        apps_ctx = [f"{a.app_name}:{a.package_name}" for a in req.installed_apps[:90]]
        ui_ctx = [f"{n.node_id}|{n.class_name}|txt={n.text}|desc={n.content_description}|clk={n.is_clickable}|edt={n.is_editable}|{n.bounds_in_screen}" for n in req.current_ui_tree[:60]]
        text_part = f"Prompt: {req.user_prompt}\nModeHint: {req.mode}\nActivePkg: {req.active_package}\nActiveActivity: {req.active_activity}\nHistory: {req.history[-10:]}\nInstalledApps: {apps_ctx}\nUITree: {ui_ctx}"
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
                models = tuple(dict.fromkeys((self.model_name, "gemini-3.8-flash", "gemini-3.5-flash-lite")))
                for model_id in models:
                    try:
                        cfg_args: dict = {"system_instruction": SYSTEM_PROMPT, "response_mime_type": "application/json", "response_schema": PlanResponse, "max_output_tokens": 2048, "temperature": 0.25}
                        if getattr(types, "ThinkingConfig", None):
                            cfg_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                        resp = self.client.models.generate_content(model=model_id, contents=contents, config=types.GenerateContentConfig(**cfg_args))
                        raw = (resp.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                        return self._post_validate(PlanResponse.model_validate(_sanitize_raw_plan(json.loads(raw))), req)
                    except Exception as exc:
                        logger.warning("Planner model %s fallback (%s)", model_id, exc)
        except Exception as outer:
            logger.error("Unexpected planner failure recovered: %s", outer)
        return build_fallback_plan(req)

    def _post_validate(self, parsed: PlanResponse, req: PlanRequest) -> PlanResponse:
        scene_items = parsed.primitives or parsed.canvas_scene
        if (parsed.mode == "EXPLAIN" or parsed.next_action.action_type == "CANVAS_EXPLAIN") and not scene_items:
            title = parsed.scene_title or extract_explain_title(req.user_prompt)
            return parsed.model_copy(update={"mode": "EXPLAIN", "scene_title": title, "next_action": NextAction(action_type="CANVAS_EXPLAIN")})
        if scene_items and (parsed.primitives is None or parsed.canvas_scene is None):
            return parsed.model_copy(update={"primitives": scene_items, "canvas_scene": scene_items})
        return parsed


planner = TaskPlanner()


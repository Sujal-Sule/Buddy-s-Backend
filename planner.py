import json
import logging
import os
import re
from models import AppCatalogEntry, CanvasDrawInstructions, CanvasEdge, CanvasNode, PlanRequest, PlanResponse, TaskStep

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

SYSTEM_INSTRUCTION = (
    "You are The Buddy, an Autonomous Android OS Agent & Visual Tutor. Return ONLY valid JSON matching PlanResponse:\n"
    '{"status":"ok","mode":"TYPE_OS_ACTION"|"TYPE_CONVERSATION","original_prompt":"...","speech_reply":"...","steps":[{"step":1,"action_type":"LAUNCH_INTENT"|"WHATSAPP_SEND"|"SCREENSHOT"|"SYSTEM_SETTING"|"CLICK"|"TYPE"|"SCROLL"|"BACK"|"HOME"|"VERIFY_SUCCESS","target":"...","payload":"...","confirmation_required":false}],"canvas_draw_instructions":null}\n'
    "Rules:\n"
    "1. ALWAYS think first and provide a natural, conversational female-persona speech_reply describing what you are doing.\n"
    "2. If the user wants OS or in-app actions across ANY app (e.g., 'open youtube and play maari song', 'open spotify and play starboy', 'open instagram and scroll down', 'click Reels'), set mode='TYPE_OS_ACTION', populate sequential 'steps', and set 'canvas_draw_instructions': null.\n"
    "3. ONLY when the user explicitly asks to explain a concept, how something works, or requests a diagram/canvas (and NOT an app action), set mode='TYPE_CONVERSATION', 'steps': [], and populate 'canvas_draw_instructions' with 4 topic-specific nodes, 3 edges, and 3 flow_steps."
)


def is_explicit_os_action(prompt: str) -> bool:
    l = re.sub(r"\bpaly\b", "play", prompt.lower().strip())
    action_kw = ("open ", "launch ", "start ", "play ", "youtube", "spotify", "whatsapp", "instagram", "scroll", "swipe", "click ", "tap ", "search ", "message ", "send ", "screenshot", "setting", " song", " video")
    starts_explain = l.startswith(("explain ", "how does ", "how do ", "what is ", "why does ", "draw ", "visualize ")) and "open " not in l and "play " not in l and "youtube" not in l
    return any(k in l for k in action_kw) and not starts_explain


def sanitize_youtube_query(raw_query: str) -> str:
    norm = re.sub(r"\bpaly\b", "play", raw_query.strip(), flags=re.IGNORECASE)
    first = re.split(r"\s+(?:and\s+then|and\s+send|and\s+message|and\s+take|and\s+scroll|then\s+)\s+", norm, flags=re.IGNORECASE)[0]
    cleaned = re.sub(
        r"^(?:hey\s+buddy\s*,?\s*|buddy\s*,?\s*)?(?:can\s+you\s+|could\s+you\s+|would\s+you\s+|will\s+you\s+)?(?:please\s+)?(?:open\s+(?:the\s+)?youtube\s+and\s+play\s+|open\s+and\s+play\s+|open\s+(?:the\s+)?youtube\s+and\s+search\s+|open\s+(?:the\s+)?youtube\s+|can\s+you\s+play\s+|play\s+|search\s+for\s+|search\s+|watch\s+|listen\s+to\s+|find\s+)+",
        "", first, flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
    for _ in range(3):
        cleaned = re.sub(r"\s+(?:song\s+on\s+it|video\s+on\s+it|video\s+for\s+me|song\s+for\s+me|on\s+youtube|in\s+youtube|from\s+youtube|on\s+it|for\s+me)\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(?:song|video|music\s+video|music|track|audio|official\s+video)s?\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:the|a|an)\s+", "", cleaned, flags=re.IGNORECASE).strip(" .,!?\"'")
    return (cleaned.title() if cleaned.islower() else cleaned) if cleaned else "Music"


def build_explanation_scene(prompt: str) -> CanvasDrawInstructions:
    topic = re.sub(r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:explain\s+me\s+|explain\s+how\s+|explain\s+|what\s+is\s+|how\s+does\s+|how\s+do\s+|draw\s+|visualize\s+)", "", prompt.strip(), flags=re.IGNORECASE)
    topic = re.sub(r"\s+(?:on\s+canvas|works?)\??$", "", topic, flags=re.IGNORECASE).strip(" ?.") or "System Architecture"
    title = topic.title()[:28]
    return CanvasDrawInstructions(
        title=title, summary=f"Interactive visual breakdown of {title}",
        nodes=[
            CanvasNode(id="n1", label="1. Input & Trigger", sublabel=f"Initiate {title}", shape="ROUND_RECT", x_ratio=0.5, y_ratio=0.18, color_hex="#6366F1"),
            CanvasNode(id="n2", label="2. Core Mechanism", sublabel="State & Encoding", shape="CIRCLE", x_ratio=0.28, y_ratio=0.50, color_hex="#06B6D4"),
            CanvasNode(id="n3", label="3. Dynamic Processing", sublabel="Active Transformation", shape="DIAMOND", x_ratio=0.72, y_ratio=0.50, color_hex="#EC4899"),
            CanvasNode(id="n4", label="4. Final Output", sublabel=f"Verified {title}", shape="ROUND_RECT", x_ratio=0.5, y_ratio=0.82, color_hex="#22C55E"),
        ],
        edges=[CanvasEdge(from_id="n1", to_id="n2", label="Encode"), CanvasEdge(from_id="n2", to_id="n3", label="Process"), CanvasEdge(from_id="n3", to_id="n4", label="Synthesize")],
        flow_steps=[f"Capture initial input for {title}", "Execute core mechanism & transformation", "Deliver verified output"],
    )


class TaskPlanner:
    def __init__(self) -> None:
        self.model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        has_valid_key = bool(api_key) and api_key != "your_gemini_api_key_here" and genai is not None
        try:
            self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"}) if has_valid_key else None
        except Exception:
            self.client = genai.Client(api_key=api_key) if has_valid_key else None

    def decompose_task(self, user_prompt: str, req: PlanRequest | None = None) -> PlanResponse:
        cleaned = re.sub(r"\bpaly\b", "play", user_prompt.strip(), flags=re.IGNORECASE)
        catalog = req.app_catalog if req else []
        ui_nodes = req.ui_hierarchy[:22] if req else []
        force_action = is_explicit_os_action(cleaned)
        if self.client and types is not None:
            ctx = f"Prompt: {cleaned}\nActivePkg: {req.active_package if req else ''}\nApps: {[f'{a.label}:{a.package_name}' for a in catalog[:45]]}\nUI: {[f'{n.node_id}:{n.text or n.content_desc}@{n.bounds}' for n in ui_nodes]}"
            for model_id in (self.model_name, "gemini-2.5-flash-lite", "gemini-2.5-flash"):
                try:
                    cfg_args: dict = {"system_instruction": SYSTEM_INSTRUCTION, "response_mime_type": "application/json", "temperature": 0.15}
                    if getattr(types, "ThinkingConfig", None) and "2.5" in model_id:
                        cfg_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                    resp = self.client.models.generate_content(model=model_id, contents=ctx, config=types.GenerateContentConfig(**cfg_args))
                    raw = (resp.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                    parsed = PlanResponse.model_validate(json.loads(raw))
                    steps = [
                        TaskStep(
                            step=i + 1, action_type=s.action_type, target=s.target,
                            payload=sanitize_youtube_query(s.payload or cleaned) if s.action_type == "LAUNCH_INTENT" and "youtube" in s.target.lower() else s.payload,
                            confirmation_required=s.confirmation_required,
                        )
                        for i, s in enumerate(parsed.steps)
                    ]
                    if force_action:
                        if not steps:
                            return self.build_fallback_plan(cleaned, catalog)
                        return parsed.model_copy(update={"mode": "TYPE_OS_ACTION", "original_prompt": cleaned, "steps": steps, "canvas_draw_instructions": None})
                    canvas = parsed.canvas_draw_instructions
                    if (parsed.mode == "TYPE_CONVERSATION" or not steps) and (canvas is None or not canvas.nodes):
                        canvas = build_explanation_scene(cleaned)
                    return parsed.model_copy(update={"original_prompt": cleaned, "steps": steps, "canvas_draw_instructions": canvas})
                except Exception as exc:
                    logger.warning("Model %s fallback (%s)", model_id, exc)
        return self.build_fallback_plan(cleaned, catalog)

    def build_fallback_plan(self, user_prompt: str, catalog: list[AppCatalogEntry] | None = None) -> PlanResponse:
        cleaned = re.sub(r"\bpaly\b", "play", user_prompt.strip(), flags=re.IGNORECASE); lower = cleaned.lower()
        if not is_explicit_os_action(cleaned) and any(k in lower for k in ("explain", "how does", "how do", "what is", "why does", "teach me", "diagram", "canvas", "visualize")):
            scene = build_explanation_scene(cleaned)
            return PlanResponse(status="ok", mode="TYPE_CONVERSATION", original_prompt=cleaned, speech_reply=f"Here is how {scene.title} works step by step on your visual canvas.", steps=[], canvas_draw_instructions=scene)

        m_open_play = re.match(r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:open|launch|start)\s+(?:the\s+)?([A-Za-z0-9_ .]+?)\s+and\s+(?:play|search\s+for|search|find|watch|listen\s+to)\s+(.+)$", cleaned, flags=re.IGNORECASE)
        if m_open_play:
            app_q = m_open_play.group(1).strip().lower()
            q = sanitize_youtube_query(m_open_play.group(2).strip())
            pkg = "com.google.android.youtube" if "youtube" in app_q else next((a.package_name for a in (catalog or []) if len(a.label) >= 3 and a.label.lower() in app_q), app_q)
            return PlanResponse(status="ok", mode="TYPE_OS_ACTION", original_prompt=cleaned, speech_reply=f"Opening {app_q} and playing {q}.", steps=[TaskStep(step=1, action_type="LAUNCH_INTENT", target=pkg, payload=q)], canvas_draw_instructions=None)

        steps: list[TaskStep] = []
        for clause in re.split(r"\s+(?:and\s+then|and|then)\s+", cleaned, flags=re.IGNORECASE):
            cl = clause.strip().lower()
            if "youtube" in cl or cl.startswith("play ") or " song" in cl or " video" in cl:
                steps.append(TaskStep(step=len(steps) + 1, action_type="LAUNCH_INTENT", target="com.google.android.youtube", payload=sanitize_youtube_query(clause)))
            elif "whatsapp" in cl or cl.startswith("message "):
                m = re.search(r"(?:to|contact)\s+([A-Za-z0-9_ ]+?)\s+(?:saying|that|message|:)\s+(.+)$", clause, flags=re.IGNORECASE)
                t, p = (m.group(1).strip(), m.group(2).strip()) if m else ("", clause)
                steps.append(TaskStep(step=len(steps) + 1, action_type="WHATSAPP_SEND", target=t, payload=p))
            elif "scroll" in cl or "swipe" in cl:
                d = "UP" if "up" in cl else ("LEFT" if "left" in cl else ("RIGHT" if "right" in cl else "DOWN"))
                steps.append(TaskStep(step=len(steps) + 1, action_type="SCROLL", target=d, payload=d))
            elif cl.startswith(("click ", "tap ", "press ")):
                lbl = re.sub(r"^(?:click|tap|press)\s+(?:on\s+|the\s+)?", "", clause.strip(), flags=re.IGNORECASE)
                steps.append(TaskStep(step=len(steps) + 1, action_type="CLICK", target=lbl, payload=lbl))
            elif cl.startswith(("type ", "search ")):
                txt = re.sub(r"^(?:type|search\s+for|search)\s+", "", clause.strip(), flags=re.IGNORECASE)
                steps.append(TaskStep(step=len(steps) + 1, action_type="TYPE", target="search", payload=txt))
            elif "setting" in cl or "wifi" in cl or "bluetooth" in cl:
                steps.append(TaskStep(step=len(steps) + 1, action_type="SYSTEM_SETTING", target="settings"))
            elif "screenshot" in cl:
                steps.append(TaskStep(step=len(steps) + 1, action_type="SCREENSHOT", target="system"))
            elif cl.startswith(("open ", "launch ", "start ")):
                app_q = re.sub(r"^(?:open|launch|start)\s+(?:the\s+)?", "", cl).strip()
                pkg = "com.google.android.youtube" if "youtube" in app_q else next((a.package_name for a in (catalog or []) if len(a.label) >= 3 and a.label.lower() in app_q), app_q)
                steps.append(TaskStep(step=len(steps) + 1, action_type="LAUNCH_INTENT", target=pkg))
        if not steps:
            pkg = next((a.package_name for a in (catalog or []) if len(a.label) >= 3 and a.label.lower() in lower), None)
            if pkg:
                steps.append(TaskStep(step=1, action_type="LAUNCH_INTENT", target=pkg))
            else:
                scene = build_explanation_scene(cleaned)
                return PlanResponse(status="ok", mode="TYPE_CONVERSATION", original_prompt=cleaned, speech_reply=f"Here is a visual explanation of {scene.title}.", steps=[], canvas_draw_instructions=scene)
        return PlanResponse(status="ok", mode="TYPE_OS_ACTION", original_prompt=cleaned, speech_reply=f"I have planned {len(steps)} live-screen step(s) and am executing them now.", steps=steps, canvas_draw_instructions=None)


planner = TaskPlanner()


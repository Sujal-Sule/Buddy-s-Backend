import re
from models import CanvasPrimitive, InstalledApp, NextAction, PlanRequest, PlanResponse, UiNode

EXPLAIN_PREFIXES = ("explain", "how does", "how do", "what is", "why does", "diagram", "visualize", "teach me")
ACTION_VERBS = ("open ", "launch ", "start ", "play ", "scroll", "swipe", "click ", "tap ", "type ", "search ", "send ", "post ", "update ", "write ", "screenshot", "back", "home")
SENSITIVE_TERMS = ("send ", "post ", "publish", "delete", "remove", "pay ", "transfer", "submit")


def detect_mode(prompt: str, requested_mode: str) -> str:
    low = prompt.lower().strip()
    if requested_mode == "EXPLAIN" or (any(low.startswith(p) for p in EXPLAIN_PREFIXES) and not any(v in low for v in ("open ", "launch ", "click "))):
        return "EXPLAIN"
    if any(k in low for k in ACTION_VERBS):
        return "ACTION"
    if requested_mode == "CONVERSATION" or low.endswith("?"):
        return "CONVERSATION"
    return "ACTION"


def build_explain_primitives(prompt: str) -> tuple[str, str, list[CanvasPrimitive]]:
    topic = re.sub(r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:explain\s+how\s+|explain\s+|what\s+is\s+|how\s+does\s+|how\s+do\s+|visualize\s+)", "", prompt.strip(), flags=re.IGNORECASE)
    topic = re.sub(r"\s+(?:works?|on\s+canvas)\??$", "", topic, flags=re.IGNORECASE).strip(" ?.") or "System Architecture"
    title = topic.title()[:32]
    primitives = [
        CanvasPrimitive(type="box", id="b1", label="1. Input Signal", sublabel=f"Trigger for {title}", x=0.50, y=0.16, color="#6366F1", step_index=1, narration=f"First, raw inputs enter the {title} pipeline and get normalized."),
        CanvasPrimitive(type="arrow", id="a1", label="Encode", from_x=0.50, from_y=0.22, to_x=0.28, to_y=0.40, color="#38BDF8", step_index=2),
        CanvasPrimitive(type="box", id="b2", label="2. Core Engine", sublabel="State & Feature Map", x=0.28, y=0.46, color="#06B6D4", step_index=2, narration="Next, the core engine maps patterns and balances internal state."),
        CanvasPrimitive(type="arrow", id="a2", label="Transform", from_x=0.44, from_y=0.46, to_x=0.56, to_y=0.46, color="#EC4899", step_index=3),
        CanvasPrimitive(type="box", id="b3", label="3. Synthesis", sublabel="Iterative Refinement", x=0.72, y=0.46, color="#EC4899", step_index=3, narration="Then synthesis refines key signals while filtering out noise."),
        CanvasPrimitive(type="highlight", id="h1", label="Active Loop", x=0.72, y=0.46, width=0.44, height=0.14, color="#F59E0B", step_index=3),
        CanvasPrimitive(type="arrow", id="a3", label="Deliver", from_x=0.72, from_y=0.52, to_x=0.50, to_y=0.72, color="#22C55E", step_index=4),
        CanvasPrimitive(type="box", id="b4", label="4. Final Output", sublabel=f"Verified {title}", x=0.50, y=0.78, color="#22C55E", step_index=4, narration=f"Finally, everything converges into the verified {title} result."),
        CanvasPrimitive(type="label", id="l1", label="Closed-Loop Flow", x=0.50, y=0.90, color="#94A3B8", step_index=4),
    ]
    return title, f"Interactive visual breakdown of {title}", primitives


def match_installed_app(prompt_lower: str, apps: list[InstalledApp]) -> InstalledApp | None:
    best: InstalledApp | None = None
    best_len = 0
    for app in apps:
        name_l = app.app_name.lower().strip()
        if len(name_l) >= 3 and name_l in prompt_lower and len(name_l) > best_len:
            best = app
            best_len = len(name_l)
    return best


def find_matching_ui_node(query: str, ui_tree: list[UiNode], editable_only: bool = False) -> UiNode | None:
    q = query.lower().strip()
    if not q:
        return None
    for node in ui_tree:
        if editable_only and not node.is_editable:
            continue
        haystack = f"{node.text} {node.content_description}".lower()
        if q in haystack and "sponsored" not in haystack and haystack.strip() != "ad":
            return node
    return None


def build_fallback_plan(req: PlanRequest) -> PlanResponse:
    prompt = req.user_prompt.strip()
    low = prompt.lower()
    mode = detect_mode(prompt, req.mode)
    if mode == "EXPLAIN":
        title, summary, scene = build_explain_primitives(prompt)
        return PlanResponse(
            status="ok", mode="EXPLAIN",
            speech_reply=f"Let's walk through {title} step by step on your visual canvas.",
            emotional_context="calm_analytical",
            next_action=NextAction(action_type="DONE"),
            scene_title=title, scene_summary=summary, canvas_scene=scene,
        )
    if mode == "CONVERSATION":
        return PlanResponse(
            status="ok", mode="CONVERSATION",
            speech_reply=f"I heard you ask about {prompt}. Ready whenever you want me to take action or explain on canvas.",
            emotional_context="warm",
            next_action=NextAction(action_type="DONE"),
        )
    matched_app = match_installed_app(low, req.installed_apps)
    if matched_app and (not req.active_package or matched_app.package_name.lower() != req.active_package.lower()) and not req.history:
        return PlanResponse(
            status="ok", mode="ACTION",
            speech_reply=f"Opening {matched_app.app_name}.",
            emotional_context="warm",
            next_action=NextAction(action_type="LAUNCH_APP", target=matched_app.package_name, payload=matched_app.app_name),
        )
    if any(k in low for k in ("update ", "write ", "bio", "lyrics", "guide me", "help me")):
        editable = next((n for n in req.current_ui_tree if n.is_editable), None)
        target_label = editable.text or editable.content_description or editable.node_id if editable else "input field"
        draft = f"Draft for {prompt}"
        return PlanResponse(
            status="ok", mode="ACTION",
            speech_reply="I prepared a draft and highlighted the target field for you.",
            emotional_context="warm",
            next_action=NextAction(
                action_type="SPOTLIGHT_GUIDE", target=target_label, payload=draft,
                draft_content=draft, instruction="Tap Auto-Fill to insert this draft into the active field.",
            ),
        )
    if "screenshot" in low:
        return PlanResponse(status="ok", mode="ACTION", speech_reply="Capturing screenshot.", next_action=NextAction(action_type="SCREENSHOT", target="system"))
    if "scroll" in low or "swipe" in low:
        direction = "UP" if "up" in low else ("LEFT" if "left" in low else ("RIGHT" if "right" in low else "DOWN"))
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Scrolling {direction.lower()}.", next_action=NextAction(action_type="SCROLL", target=direction))
    if low in ("back", "go back"):
        return PlanResponse(status="ok", mode="ACTION", speech_reply="Going back.", next_action=NextAction(action_type="BACK", target="system"))
    if "go home" in low or low == "home":
        return PlanResponse(status="ok", mode="ACTION", speech_reply="Returning to home screen.", next_action=NextAction(action_type="GLOBAL_HOME", target="system"))
    requires_conf = any(t in low for t in SENSITIVE_TERMS)
    click_m = re.search(r"(?:click|tap|press|open)\s+(.+)$", low)
    if click_m:
        cand = click_m.group(1).strip()
        node = find_matching_ui_node(cand, req.current_ui_tree)
        if node:
            return PlanResponse(
                status="ok", mode="ACTION",
                speech_reply=f"Shall I tap {node.text or node.content_description}?" if requires_conf else f"Tapping {node.text or node.content_description}.",
                emotional_context="cautious" if requires_conf else "warm",
                next_action=NextAction(action_type="CLICK_NODE", target=node.node_id, payload=node.text or cand, requires_confirmation=requires_conf),
            )
    return PlanResponse(status="ok", mode="ACTION", speech_reply="All caught up.", next_action=NextAction(action_type="DONE"))

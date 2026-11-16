import re
from models import CanvasPrimitive, InstalledApp, NextAction, PlanRequest, PlanResponse, UiNode

EXPLAIN_PREFIXES = ("explain", "how does", "how do", "what is", "why does", "diagram", "visualize", "teach me")
ACTION_VERBS = ("open ", "launch ", "start ", "play ", "scroll", "swipe", "click ", "tap ", "type ", "search ", "find ", "send ", "message ", "post ", "update ", "write ", "screenshot", "back", "home", "fill ", "summarize", "translate", "compare")
SENSITIVE_TERMS = ("send ", "post ", "publish", "delete ", "remove ", "pay ", "transfer", "submit")
NAV_TABS = {"chats", "updates", "communities", "calls", "home", "shorts", "subscriptions", "library", "explore", "inbox"}
FILLER_WORDS = {"the", "a", "an", "my", "group", "chat", "channel", "page", "profile", "video", "song", "button", "item", "tab", "app", "on", "in"}


def detect_mode(prompt: str, requested_mode: str) -> str:
    low = prompt.lower().strip()
    if requested_mode == "SCREEN_READ" or low.startswith(("summarize", "translate", "read this")):
        return "SCREEN_READ"
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
        CanvasPrimitive(type="box", id="b1", label="1. Input Signal", sublabel=f"Trigger for {title}", x=500, y=140, width=520, height=120, color="#6366F1", step_index=1, narration=f"First, raw inputs enter the {title} pipeline and get normalized."),
        CanvasPrimitive(type="arrow", id="a1", label="Encode", from_x=500, from_y=205, to_x=270, to_y=395, color="#06B6D4", step_index=2),
        CanvasPrimitive(type="box", id="b2", label="2. Core Engine", sublabel="State & Feature Map", x=270, y=460, width=420, height=125, color="#06B6D4", step_index=2, narration="Next, the core engine maps patterns and balances internal state."),
        CanvasPrimitive(type="arrow", id="a2", label="Transform", from_x=480, from_y=460, to_x=520, to_y=460, color="#EC4899", step_index=3),
        CanvasPrimitive(type="box", id="b3", label="3. Synthesis", sublabel="Iterative Refinement", x=730, y=460, width=420, height=125, color="#EC4899", step_index=3, narration="Then synthesis refines key signals while filtering out noise."),
        CanvasPrimitive(type="highlight", id="h1", label="Active Loop", x=730, y=460, width=440, height=140, color="#34D399", step_index=3),
        CanvasPrimitive(type="arrow", id="a3", label="Deliver", from_x=730, from_y=525, to_x=500, to_y=720, color="#34D399", step_index=4),
        CanvasPrimitive(type="box", id="b4", label="4. Final Output", sublabel=f"Verified {title}", x=500, y=790, width=520, height=120, color="#34D399", step_index=4, narration=f"Finally, everything converges into the verified {title} result."),
        CanvasPrimitive(type="label", id="l1", label="Closed-Loop Flow", x=500, y=925, color="#94A3B8", step_index=4),
    ]
    return title, f"Interactive visual breakdown of {title}", primitives


def match_installed_app(prompt_lower: str, apps: list[InstalledApp]) -> InstalledApp | None:
    best: InstalledApp | None = None
    best_len = 0
    for app in apps:
        name_l = app.app_name.lower().strip()
        if len(name_l) >= 2 and re.search(rf"\b{re.escape(name_l)}\b", prompt_lower) and len(name_l) > best_len:
            best = app
            best_len = len(name_l)
    return best


def extract_subgoal_query(prompt: str, app: InstalledApp | None) -> tuple[str, str, bool]:
    sub = prompt.strip()
    if app:
        esc = re.escape(app.app_name.strip())
        sub = re.sub(rf"^(?:can\s+you\s+|please\s+)?(?:open|launch|start|go\s+to|use)\s+{esc}\b", "", sub, flags=re.IGNORECASE)
        sub = re.sub(rf"\b(?:on|in|via|using|from)\s+{esc}\b", "", sub, flags=re.IGNORECASE)
        sub = re.sub(r"^\s*(?:and|then|to|,)\s+", "", sub, flags=re.IGNORECASE).strip(" ,.")
    is_search = sub.lower().startswith(("search", "find", "play", "watch", "look up"))
    stripped = re.sub(r"^(?:can\s+you\s+|please\s+)?(?:click|tap|press|open|select|go\s+to|find|search\s+for|search|look\s+up|play|watch)\s+", "", sub, flags=re.IGNORECASE).strip()
    toks = [t for t in stripped.split() if t]
    filt = [t for t in toks if t.lower() not in FILLER_WORDS]
    return sub, " ".join(filt or toks).strip(), is_search


def find_matching_ui_node(query: str, ui_tree: list[UiNode]) -> UiNode | None:
    q = query.lower().strip()
    q_norm = re.sub(r"[^a-z0-9]", "", q)
    if not q:
        return None
    tokens = [t for t in q.split() if len(t) >= 2 and t not in FILLER_WORDS]
    for node in ui_tree:
        if node.is_editable:
            continue
        txt = node.text.strip(); desc = node.content_description.strip()
        hay = f"{txt} {desc}".lower().strip()
        if not hay or hay == "ad" or "sponsored" in hay or "ask meta ai" in hay or (hay == "search" and q != "search"):
            continue
        if txt.lower() in NAV_TABS and txt.lower() not in q:
            continue
        h_norm = re.sub(r"[^a-z0-9]", "", hay)
        if txt.lower() == q or desc.lower() == q or q in hay or (len(q_norm) >= 2 and q_norm in h_norm) or (tokens and all(t in hay for t in tokens)):
            return node
    return None


def find_search_button(ui_tree: list[UiNode]) -> UiNode | None:
    return next((n for n in ui_tree if not n.is_editable and ("search" in n.node_id.lower() or "search" in n.content_description.lower() or n.text.strip().lower() == "search")), None)


def build_fallback_plan(req: PlanRequest) -> PlanResponse:
    prompt = req.user_prompt.strip(); low = prompt.lower()
    mode = detect_mode(prompt, req.mode)
    if mode == "SCREEN_READ":
        lines = [ln.strip() for ln in prompt.splitlines() if len(ln.strip()) > 15 and not ln.lower().startswith("screen_read")]
        bullets = lines[:4] if lines else ["Screen content captured for reading."]
        return PlanResponse(status="ok", mode="SCREEN_READ", speech_reply=" ".join(bullets[:2]), emotional_context="calm_analytical", next_action=NextAction(action_type="SCREEN_READ"), summary_bullets=bullets, translated_text=" ".join(bullets) if "translate" in low else "")
    if mode == "EXPLAIN":
        title, summary, scene = build_explain_primitives(prompt)
        return PlanResponse(status="ok", mode="EXPLAIN", speech_reply=f"Let's walk through {title} step by step on your visual canvas.", emotional_context="calm_analytical", next_action=NextAction(action_type="CANVAS_EXPLAIN"), scene_title=title, scene_summary=summary, canvas_scene=scene)
    if "fill this form" in low or "auto-fill" in low or "autofill" in low:
        return PlanResponse(status="ok", mode="FORM_FILL", speech_reply="Auto-filling your profile details.", next_action=NextAction(action_type="FORM_FILL"))
    if any(k in low for k in ("screenshot", "latest photo", "ticket")) and any(k in low for k in ("find", "send", "share", "clean")):
        return PlanResponse(status="ok", mode="ACTION", speech_reply="Searching your media library.", next_action=NextAction(action_type="MEDIA_SHARE", payload=prompt, requires_confirmation=("clean" in low or "delete" in low)))
    if mode == "CONVERSATION":
        return PlanResponse(status="ok", mode="CONVERSATION", speech_reply="Searching the web for that." if low.endswith("?") else "I'm ready whenever you want me to open an app or explain a topic.", next_action=NextAction(action_type="SYSTEM_INTENT" if low.endswith("?") else "DONE", target="WEB_SEARCH" if low.endswith("?") else "", payload=prompt if low.endswith("?") else None))

    matched_app = match_installed_app(low, req.installed_apps)
    sub_goal, query, is_search = extract_subgoal_query(prompt, matched_app)
    if matched_app and (not req.active_package or matched_app.package_name.lower() != req.active_package.lower()) and not any(f"LAUNCH_APP:{matched_app.package_name}" in h for h in req.history):
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opening {matched_app.app_name}.", next_action=NextAction(action_type="LAUNCH_APP", target=matched_app.package_name, payload=matched_app.app_name))
    if matched_app and not sub_goal and any(f"LAUNCH_APP:{matched_app.package_name}:true" in h for h in req.history):
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opened {matched_app.app_name}.", next_action=NextAction(action_type="DONE"))
    if "scroll" in low or "swipe" in low or "reel" in low:
        direction = "UP" if ("up" in low or "previous" in low) else "DOWN"
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Scrolling {direction.lower()}.", next_action=NextAction(action_type="NAVIGATE", target=f"scroll {direction.lower()}"))
    if low in ("back", "go back"):
        return PlanResponse(status="ok", mode="ACTION", speech_reply="Going back.", next_action=NextAction(action_type="BACK", target="system"))
    if not req.current_ui_tree and any(h.startswith("LAUNCH_APP:") for h in req.history):
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opened {matched_app.app_name if matched_app else 'the app'}. Enable Accessibility so I can tap {query or 'inside'}.", next_action=NextAction(action_type="DONE"))

    requires_conf = any(t in low for t in SENSITIVE_TERMS)
    typed_already = any(h.startswith("TYPE_TEXT:") for h in req.history)
    clicked_search = any(h.startswith("CLICK_NODE:") and "search" in h.lower() for h in req.history)
    if query:
        hit = find_matching_ui_node(query, req.current_ui_tree)
        if hit:
            if any(h.startswith(f"CLICK_NODE:{hit.node_id}:true") for h in req.history):
                return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opened {query}.", next_action=NextAction(action_type="DONE"))
            lbl = hit.text or hit.content_description or query
            return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opening {lbl}.", next_action=NextAction(action_type="CLICK_NODE", target=hit.node_id, payload=lbl, requires_confirmation=requires_conf))
        if not typed_already:
            edit_node = next((n for n in req.current_ui_tree if n.is_editable), None)
            if edit_node:
                return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Searching for {query}.", next_action=NextAction(action_type="TYPE_TEXT", target=edit_node.node_id, payload=query))
            search_btn = find_search_button(req.current_ui_tree)
            if search_btn and not clicked_search:
                return PlanResponse(status="ok", mode="ACTION", speech_reply="Opening search.", next_action=NextAction(action_type="CLICK_NODE", target=search_btn.node_id, payload="Search"))
        if is_search and typed_already:
            first_res = next((n for n in req.current_ui_tree if not n.is_editable and n.is_clickable and len(n.text) >= 4 and "search" not in n.text.lower()), None)
            if first_res and not any(h.startswith(f"CLICK_NODE:{first_res.node_id}:true") for h in req.history):
                return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Opening {first_res.text}.", next_action=NextAction(action_type="CLICK_NODE", target=first_res.node_id, payload=first_res.text))
        if sum(1 for h in req.history if h.startswith("SCROLL:")) < 2 and req.current_ui_tree:
            return PlanResponse(status="ok", mode="ACTION", speech_reply=f"Looking for {query}.", next_action=NextAction(action_type="SCROLL", target="DOWN"))
        return PlanResponse(status="ok", mode="ACTION", speech_reply=f"I couldn't find {query} on this screen.", next_action=NextAction(action_type="DONE"))
    return PlanResponse(status="ok", mode="CONVERSATION", speech_reply="Tell me what app, search, or question you want me to handle.", next_action=NextAction(action_type="DONE"))


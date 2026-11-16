import re
from models import CanvasPrimitive, NextAction, PlanResponse


def build_explain_primitives(prompt: str) -> tuple[str, str, list[CanvasPrimitive]]:
    topic = re.sub(
        r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:explain\s+how\s+|explain\s+|what\s+is\s+|how\s+does\s+|how\s+do\s+|visualize\s+|teach\s+me\s+)",
        "",
        prompt.strip(),
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\s+(?:works?|on\s+canvas|with\s+diagram)\??$", "", topic, flags=re.IGNORECASE).strip(" ?.") or "System Dynamics"
    title = topic.title()[:32]
    primitives = [
        CanvasPrimitive(
            type="svg_path", id="domain_boundary", label=f"{title} Boundary",
            d="M 140 310 C 260 215, 740 215, 860 310 L 860 650 C 740 745, 260 745, 140 650 Z",
            strokeColor="#334155", fillColor="#146366F1", strokeWidth=3.0, step_index=1,
            narration=f"First, signals and raw inputs enter the {title} envelope.",
        ),
        CanvasPrimitive(
            type="state_morph", id="intake_oscillator", label="Input State",
            x=245, y=480, width=96, height=130, axis="Y", amplitude=24.0, frequency=1.35, color="#FB7185", step_index=1,
        ),
        CanvasPrimitive(
            type="procedural_polygon", id="core_node", label="Primary Transform",
            cx=485, cy=480, sides=12, innerRadius=56, outerRadius=78, angularVelocity=96.0, direction="CW",
            color="#38BDF8", step_index=2,
            narration=f"Next, the central stage couples and transforms energy inside {title}.",
        ),
        CanvasPrimitive(
            type="radial_array", id="harmonic_ring", label="Coupled Stage",
            cx=655, cy=480, sides=8, innerRadius=36, outerRadius=66, angularVelocity=115.0, direction="CCW",
            color="#818CF8", step_index=2,
        ),
        CanvasPrimitive(
            type="state_morph", id="pulse_gate", label="Modulation Pulse",
            x=790, y=480, width=90, height=90, axis="SCALE", amplitude=18.0, frequency=1.6, color="#34D399", step_index=3,
            narration="Then downstream regulation shapes amplitude and timing cleanly.",
        ),
        CanvasPrimitive(
            type="flow_spline", id="primary_stream",
            startX=245, startY=480, cp1X=360, cp1Y=335, cp2X=560, cp2Y=335, endX=790, endY=480,
            particleColor="#38BDF8", animatedFlow=True, particleCount=3, flowSpeed=0.45, step_index=3,
        ),
        CanvasPrimitive(
            type="flow_spline", id="feedback_stream",
            startX=790, startY=505, cp1X=620, cp1Y=650, cp2X=390, cp2Y=650, endX=245, endY=505,
            particleColor="#34D399", animatedFlow=True, particleCount=3, flowSpeed=0.38, step_index=4,
            narration=f"Finally, feedback stabilizes the {title} output cycle.",
        ),
        CanvasPrimitive(type="callout_tag", id="tag_in", title="1. Intake", subtitle="Initial State", x=220, y=215, targetX=245, targetY=420, color="#FB7185", step_index=1),
        CanvasPrimitive(type="callout_tag", id="tag_core", title="2. Core Coupling", subtitle=title[:22], x=545, y=215, targetX=485, targetY=415, color="#38BDF8", step_index=2),
        CanvasPrimitive(type="callout_tag", id="tag_out", title="3. Output & Feedback", subtitle="Closed-Loop Flow", x=765, y=735, targetX=790, targetY=525, color="#34D399", step_index=4),
    ]
    return title, f"Universal Vector Schematic • {title}", primitives


def try_creative_or_system_fallback(prompt: str, low: str) -> PlanResponse | None:
    if "joke" in low:
        return PlanResponse(mode="CONVERSATION", speech_reply="Why do programmers prefer dark mode? Because light attracts bugs.")
    if "riddle" in low:
        return PlanResponse(mode="CONVERSATION", speech_reply="What has keys that open no locks and space without a room? A keyboard.")
    if "poem" in low:
        return PlanResponse(mode="CONVERSATION", speech_reply="Quiet code humming beneath glowing glass, turning spoken intent into action fast.")
    if "quote" in low or "motivat" in low:
        return PlanResponse(mode="CONVERSATION", speech_reply="Small consistent steps beat sudden bursts every single time.")
    if any(k in low for k in ("set alarm", "set an alarm", "wake me up", "set timer", "set a timer")):
        tgt = "SET_TIMER" if "timer" in low else "SET_ALARM"
        return PlanResponse(mode="ACTION", speech_reply=f"Setting {'timer' if tgt == 'SET_TIMER' else 'alarm'}.", next_action=NextAction(action_type="SYSTEM_INTENT", target=tgt, payload=prompt))
    if "open camera" in low or "take a photo" in low or "take a selfie" in low:
        return PlanResponse(mode="ACTION", speech_reply="Opening camera.", next_action=NextAction(action_type="SYSTEM_INTENT", target="OPEN_CAMERA", payload="selfie" if "selfie" in low else ""))
    if "navigate to " in low or "directions to " in low:
        return PlanResponse(mode="ACTION", speech_reply="Opening Maps directions.", next_action=NextAction(action_type="SYSTEM_INTENT", target="MAPS_NAV", payload=prompt))
    return None


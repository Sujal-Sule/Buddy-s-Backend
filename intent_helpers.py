import re
from models import CanvasPrimitive, NextAction, PlanResponse


def build_explain_primitives(prompt: str) -> tuple[str, str, list[CanvasPrimitive]]:
    topic = re.sub(
        r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:explain\s+how\s+|explain\s+|what\s+is\s+|how\s+does\s+|how\s+do\s+|visualize\s+)",
        "",
        prompt.strip(),
        flags=re.IGNORECASE,
    )
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


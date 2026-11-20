import re
from models import NextAction, PlanResponse


def extract_explain_title(prompt: str) -> str:
    topic = re.sub(
        r"^(?:hey\s+buddy\s*,?\s*)?(?:can\s+you\s+|please\s+)?(?:explain\s+how\s+|explain\s+|what\s+is\s+|what\s+are\s+|how\s+does\s+|how\s+do\s+|visualize\s+|teach\s+me\s+|draw\s+|sketch\s+)",
        "",
        prompt.strip(),
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\s+(?:works?|work|on\s+canvas|with\s+diagram|on\s+whiteboard)\??$", "", topic, flags=re.IGNORECASE).strip(" ?.") or "Live Whiteboard"
    return topic.title()[:40]


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


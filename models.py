from typing import Literal, Optional
from pydantic import BaseModel, Field

AllowedMode = Literal["ACTION", "CONVERSATION", "EXPLAIN", "SCREEN_READ", "FORM_FILL"]

AllowedActionType = Literal[
    "FORM_FILL",
    "MEDIA_SHARE",
    "SCREEN_READ",
    "NAVIGATE",
    "CANVAS_EXPLAIN",
    "LAUNCH_APP",
    "CLICK_NODE",
    "TYPE_TEXT",
    "SCROLL",
    "BACK",
    "GLOBAL_HOME",
    "SPOTLIGHT_GUIDE",
    "SCREENSHOT",
    "SYSTEM_INTENT",
    "DONE",
]

CanvasPrimitiveType = Literal["box", "arrow", "label", "highlight"]


class InstalledApp(BaseModel):
    app_name: str
    package_name: str


class UiNode(BaseModel):
    node_id: str
    text: str = ""
    content_description: str = ""
    class_name: str = ""
    is_clickable: bool = False
    is_editable: bool = False
    bounds_in_screen: str = ""


class CanvasPrimitive(BaseModel):
    type: CanvasPrimitiveType = "box"
    id: str = ""
    label: str = ""
    sublabel: str = ""
    x: float = 500.0
    y: float = 500.0
    width: float = 420.0
    height: float = 115.0
    from_x: float = 500.0
    from_y: float = 200.0
    to_x: float = 500.0
    to_y: float = 500.0
    color: str = "#6366F1"
    step_index: int = 1
    narration: str = ""


class NextAction(BaseModel):
    action_type: AllowedActionType = "DONE"
    target: str = ""
    payload: Optional[str] = None
    draft_content: Optional[str] = None
    instruction: Optional[str] = None
    requires_confirmation: bool = False


class PlanRequest(BaseModel):
    user_prompt: str
    installed_apps: list[InstalledApp] = Field(default_factory=list)
    current_ui_tree: list[UiNode] = Field(default_factory=list)
    mode: AllowedMode = "ACTION"
    active_package: str = ""
    talk_mode: str = "COMMAND"
    history: list[str] = Field(default_factory=list)
    screen_image_base64: Optional[str] = Field(default=None, max_length=350_000)


class PlanResponse(BaseModel):
    status: str = "ok"
    mode: AllowedMode = "ACTION"
    speech_reply: str = ""
    emotional_context: str = "warm"
    next_action: NextAction = Field(default_factory=NextAction)
    scene_title: str = ""
    scene_summary: str = ""
    canvas_scene: Optional[list[CanvasPrimitive]] = None
    summary_bullets: Optional[list[str]] = None
    translated_text: str = ""


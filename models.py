from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

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

CanvasPrimitiveType = Literal[
    "svg_path",
    "procedural_polygon",
    "radial_array",
    "flow_spline",
    "state_morph",
    "callout_tag",
]


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
    model_config = ConfigDict(populate_by_name=True)

    type: CanvasPrimitiveType = "svg_path"
    id: str = ""
    label: str = ""
    sublabel: str = ""
    color: str = "#6366F1"
    step_index: int = 1
    narration: str = ""
    # Universal SVG vector geometry (0..1000 normalized grid)
    d: str = ""
    strokeColor: str = "#38BDF8"
    fillColor: str = "#2238BDF8"
    strokeWidth: float = 3.5
    # procedural_polygon / radial_array parameters
    cx: float = 500.0
    cy: float = 500.0
    sides: int = 12
    innerRadius: float = 48.0
    outerRadius: float = 72.0
    angularVelocity: float = 0.0
    direction: Literal["CW", "CCW"] = "CW"
    # state_morph physics / kinematics parameters
    x: float = 500.0
    y: float = 500.0
    width: float = 140.0
    height: float = 110.0
    axis: Literal["X", "Y", "SCALE", "OPACITY"] = "Y"
    amplitude: float = 28.0
    frequency: float = 1.2
    phaseOffset: float = 0.0
    # flow_spline Bezier particle emitter parameters
    startX: float = 200.0
    startY: float = 500.0
    cp1X: float = 400.0
    cp1Y: float = 350.0
    cp2X: float = 600.0
    cp2Y: float = 650.0
    endX: float = 800.0
    endY: float = 500.0
    particleColor: str = "#34D399"
    animatedFlow: bool = True
    particleCount: int = 3
    flowSpeed: float = 0.42
    # callout_tag leader annotation parameters
    title: str = ""
    subtitle: str = ""
    targetX: float = 500.0
    targetY: float = 500.0


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


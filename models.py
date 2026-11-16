from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

AllowedMode = Literal["ACTION", "CONVERSATION", "EXPLAIN", "SCREEN_READ", "FORM_FILL"]
AllowedActionType = Literal[
    "FORM_FILL", "MEDIA_SHARE", "SCREEN_READ", "NAVIGATE", "CANVAS_EXPLAIN",
    "LAUNCH_APP", "CLICK_NODE", "TYPE_TEXT", "SCROLL", "BACK", "GLOBAL_HOME",
    "SPOTLIGHT_GUIDE", "SCREENSHOT", "SYSTEM_INTENT", "DONE",
]
PrimitiveType = Literal["svg_path", "radial_array", "flow_spline", "state_morph", "callout_tag"]
NormCoord = Annotated[float, Field(ge=0.0, le=1000.0)]


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


class VectorPrimitive(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    type: PrimitiveType
    id: str = ""
    label: str = ""
    sublabel: str = ""
    color: str = "#6366F1"
    step_index: int = Field(default=1, ge=1, le=8)
    narration: str = ""
    # Path data (0..1000 normalized grid)
    d: str = ""
    strokeColor: str = "#38BDF8"
    fillColor: str = "#2238BDF8"
    strokeWidth: float = Field(default=3.5, ge=0.5, le=24.0)
    # Radial array / rotating geometry parameters
    cx: NormCoord = 500.0
    cy: NormCoord = 500.0
    sides: int = Field(default=12, ge=3, le=64)
    innerRadius: NormCoord = 48.0
    outerRadius: NormCoord = 72.0
    angularVelocity: float = Field(default=0.0, ge=-1440.0, le=1440.0)
    direction: Literal["CW", "CCW"] = "CW"
    # State-change animation parameters
    x: NormCoord = 500.0
    y: NormCoord = 500.0
    width: NormCoord = 140.0
    height: NormCoord = 110.0
    axis: Literal["X", "Y", "SCALE", "OPACITY", "WAVE"] = "Y"
    amplitude: float = Field(default=24.0, ge=0.0, le=500.0)
    frequency: float = Field(default=1.2, gt=0.0, le=12.0)
    phaseOffset: float = 0.0
    # Cubic Bezier flow_spline emitter parameters
    startX: NormCoord = 200.0
    startY: NormCoord = 500.0
    cp1X: NormCoord = 400.0
    cp1Y: NormCoord = 350.0
    cp2X: NormCoord = 600.0
    cp2Y: NormCoord = 650.0
    endX: NormCoord = 800.0
    endY: NormCoord = 500.0
    particleColor: str = "#34D399"
    animatedFlow: bool = True
    particleCount: int = Field(default=3, ge=1, le=12)
    flowSpeed: float = Field(default=0.42, gt=0.0, le=5.0)
    # Leader callout_tag annotation parameters
    title: str = ""
    subtitle: str = ""
    targetX: NormCoord = 500.0
    targetY: NormCoord = 500.0

    @model_validator(mode="after")
    def validate_primitive_fields(self) -> "VectorPrimitive":
        if self.type == "svg_path" and not self.d.strip():
            raise ValueError("svg_path primitive requires non-empty path data 'd'.")
        if self.type == "radial_array" and (self.outerRadius <= 0 or self.innerRadius > self.outerRadius):
            raise ValueError("radial_array requires outerRadius > 0 and innerRadius <= outerRadius.")
        if self.type == "callout_tag" and not (self.title or self.label).strip():
            raise ValueError("callout_tag primitive requires non-empty 'title' or 'label'.")
        return self


CanvasPrimitive = VectorPrimitive


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
    primitives: Optional[list[VectorPrimitive]] = None
    canvas_scene: Optional[list[VectorPrimitive]] = None
    summary_bullets: Optional[list[str]] = None
    translated_text: str = ""

    @model_validator(mode="after")
    def sync_primitives_aliases(self) -> "PlanResponse":
        if self.primitives is not None and self.canvas_scene is None:
            self.canvas_scene = self.primitives
        elif self.canvas_scene is not None and self.primitives is None:
            self.primitives = self.canvas_scene
        return self


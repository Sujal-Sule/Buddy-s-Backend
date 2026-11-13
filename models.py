from typing import Literal, Optional
from pydantic import BaseModel, Field

AllowedRequestMode = Literal["TYPE_CONVERSATION", "TYPE_OS_ACTION"]

AllowedActionType = Literal[
    "LAUNCH_INTENT",
    "WHATSAPP_SEND",
    "SCREENSHOT",
    "SYSTEM_SETTING",
    "CLICK",
    "TYPE",
    "SCROLL",
    "BACK",
    "VERIFY_SUCCESS",
]


class AppCatalogEntry(BaseModel):
    label: str
    package_name: str


class UiNodeSummary(BaseModel):
    node_id: str
    class_name: str = ""
    text: str = ""
    content_desc: str = ""
    bounds: str = ""
    clickable: bool = False
    editable: bool = False


class CanvasNode(BaseModel):
    id: str
    label: str
    sublabel: str = ""
    shape: str = "ROUND_RECT"
    x_ratio: float = 0.5
    y_ratio: float = 0.25
    color_hex: str = "#6366F1"


class CanvasEdge(BaseModel):
    from_id: str
    to_id: str
    label: str = ""


class CanvasDrawInstructions(BaseModel):
    title: str
    summary: str = ""
    nodes: list[CanvasNode] = Field(default_factory=list)
    edges: list[CanvasEdge] = Field(default_factory=list)
    flow_steps: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    user_prompt: str
    talk_mode: str = "COMMAND"
    active_package: str = ""
    app_catalog: list[AppCatalogEntry] = Field(default_factory=list)
    ui_hierarchy: list[UiNodeSummary] = Field(default_factory=list)


class TaskStep(BaseModel):
    step: int
    action_type: AllowedActionType
    target: str
    payload: Optional[str] = None
    confirmation_required: bool = False


class PlanResponse(BaseModel):
    status: str = "ok"
    mode: AllowedRequestMode = "TYPE_OS_ACTION"
    original_prompt: str
    speech_reply: str = ""
    steps: list[TaskStep] = Field(default_factory=list)
    canvas_draw_instructions: Optional[CanvasDrawInstructions] = None


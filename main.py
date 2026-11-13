import logging
import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from fallback_planner import build_fallback_plan
from models import PlanRequest, PlanResponse
from planner import DEFAULT_MODEL, planner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TheBuddyBackend")

app = FastAPI(
    title="Project Buddy Brain",
    description="Gemini 3.5 Flash-Lite Closed-Loop OS Agent & Visual Explanation Backend",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Global exception recovered: %s\n%s", exc, traceback.format_exc())
    fallback = build_fallback_plan(PlanRequest(user_prompt=""))
    return JSONResponse(status_code=200, content=fallback.model_dump())


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "Project-Buddy-Brain", "model": planner.model_name or DEFAULT_MODEL}


@app.post("/api/v1/plan", response_model=PlanResponse)
async def create_task_plan(request: PlanRequest) -> JSONResponse:
    try:
        logger.info(
            "POST /api/v1/plan mode=%s apps=%d ui_nodes=%d prompt=%r",
            request.mode,
            len(request.installed_apps),
            len(request.current_ui_tree),
            request.user_prompt,
        )
        plan_response = planner.plan_next(request)
        return JSONResponse(status_code=200, content=plan_response.model_dump())
    except Exception as exc:
        logger.error("Plan error recovered: %s\n%s", exc, traceback.format_exc())
        fallback = build_fallback_plan(request)
        return JSONResponse(status_code=200, content=fallback.model_dump())


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)

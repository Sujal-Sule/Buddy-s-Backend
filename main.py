import logging
import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from models import PlanRequest, PlanResponse
from planner import DEFAULT_MODEL, planner

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TheBuddyBackend")

app = FastAPI(
    title="The-Buddy-Planner",
    description="Gemini 3.5 Flash-Lite Autonomous OS Agent & Visual Canvas Brain",
    version="2.0.0",
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
    logging.error(traceback.format_exc())
    fallback_plan = planner.build_fallback_plan("")
    return JSONResponse(status_code=200, content=fallback_plan.model_dump())


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "The-Buddy-Planner", "model": planner.model_name or DEFAULT_MODEL}


@app.post("/api/v1/plan", response_model=PlanResponse)
async def create_task_plan(request: PlanRequest) -> JSONResponse:
    try:
        logger.info(
            "Incoming /api/v1/plan prompt=%r talk_mode=%s apps=%d ui_nodes=%d",
            request.user_prompt,
            request.talk_mode,
            len(request.app_catalog),
            len(request.ui_hierarchy),
        )
        plan_response = planner.decompose_task(request.user_prompt, request)
        return JSONResponse(status_code=200, content=plan_response.model_dump())
    except Exception:
        logging.error(traceback.format_exc())
        fallback_plan = planner.build_fallback_plan(
            getattr(request, "user_prompt", ""),
            getattr(request, "app_catalog", None),
        )
        return JSONResponse(status_code=200, content=fallback_plan.model_dump())


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


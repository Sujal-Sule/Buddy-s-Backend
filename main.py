from collections import defaultdict, deque
import json
import logging
import os
import time
import traceback
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from fallback_planner import build_fallback_plan
from models import PlanRequest, PlanResponse
from planner import DEFAULT_MODEL, planner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TheBuddyBackend")

app = FastAPI(title="Project Buddy Brain", description="Gemini 2.5 Flash Multimodal Closed-Loop OS Agent Backend", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_RATE_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT = max(10, int(os.getenv("BUDDY_RATE_LIMIT_PER_MIN", "45")))


def _verify_auth_and_rate(req: Request, authorization: str | None) -> None:
    token = os.getenv("BUDDY_API_TOKEN", "").strip()
    if token and token != "optional_bearer_token":
        supplied = (authorization or "").removeprefix("Bearer ").strip()
        if supplied != token:
            raise HTTPException(status_code=401, detail="Invalid or missing Bearer token.")
    ip = (req.client.host if req.client else "unknown")
    now = time.monotonic()
    q = _RATE_WINDOWS[ip]
    while q and now - q[0] > 60.0:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Retry shortly.")
    q.append(now)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Global exception recovered: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(status_code=200, content=build_fallback_plan(PlanRequest(user_prompt="")).model_dump())


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "Project-Buddy-Brain", "model": planner.model_name or DEFAULT_MODEL}


@app.post("/api/v1/plan", response_model=PlanResponse)
async def create_task_plan(req_obj: Request, request: PlanRequest, authorization: str | None = Header(default=None)) -> JSONResponse:
    _verify_auth_and_rate(req_obj, authorization)
    try:
        logger.info("POST /api/v1/plan mode=%s apps=%d nodes=%d vision=%s", request.mode, len(request.installed_apps), len(request.current_ui_tree), bool(request.screen_image_base64))
        return JSONResponse(status_code=200, content=planner.plan_next(request).model_dump())
    except Exception as exc:
        logger.error("Plan error recovered: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(status_code=200, content=build_fallback_plan(request).model_dump())


@app.post("/api/v1/plan/stream")
async def stream_task_plan(req_obj: Request, request: PlanRequest, authorization: str | None = Header(default=None)) -> StreamingResponse:
    _verify_auth_and_rate(req_obj, authorization)

    def event_stream():
        yield json.dumps({"event": "thinking", "status": "Perceiving screen & reasoning..."}) + "\n"
        try:
            res = planner.plan_next(request)
        except Exception as exc:
            logger.error("Stream plan recovered: %s", exc)
            res = build_fallback_plan(request)
        yield json.dumps({"event": "plan", "data": res.model_dump()}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")), reload=False)


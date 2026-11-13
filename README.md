# The Buddy — Autonomous OS Agent & Planner Backend

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%20API-orange.svg)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

**The Buddy** is a Jarvis-inspired autonomous OS agent and visual reasoning assistant. This repository contains the core intelligence and task planning backend that converts user voice commands and natural language requests into structured, executable device action sequences and interactive visual canvas diagrams.

---

## Architecture Overview

```
                      +---------------------------------------+
                      |       The Buddy Client / Device       |
                      |   (Voice Input, UI Tree, App Catalog) |
                      +-------------------+-------------------+
                                          |
                                HTTP POST /api/v1/plan
                                          v
                      +---------------------------------------+
                      |         FastAPI Planner Backend       |
                      |      (Input Normalization & Routing)   |
                      +-------------------+-------------------+
                                          |
                         +----------------+----------------+
                         |                                 |
                         v                                 v
        +---------------------------------+  +-------------------------------+
        |    Gemini Multimodal LLM Engine |  |    Deterministic Fallback     |
        |  (gemini-3.5-flash-lite, JSON)  |  |   (Rule-based Regex Engine)   |
        +----------------+----------------+  +---------------+---------------+
                         |                                   |
                         +----------------+------------------+
                                          v
                      +---------------------------------------+
                      |             PlanResponse              |
                      |  - Conversational Voice Synthesis     |
                      |  - Sequential OS Action Pipeline      |
                      |  - Interactive Canvas Visualization   |
                      +---------------------------------------+
```

---

## Core Capabilities

- **Autonomous Multi-Step OS Execution (`TYPE_OS_ACTION`)**
  Decomposes high-level instructions (e.g., *"Open YouTube and play Maari song"*, *"Send a WhatsApp message to Alex"*, *"Scroll down and click Reels"*) into atomic action primitives that the client runtime executes.

- **Interactive Whiteboard & Visual Canvas Brain (`TYPE_CONVERSATION`)**
  When users ask conceptual questions (e.g., *"Explain how neural networks work on canvas"*), the planner generates structured visual graph primitives (nodes, relational edges, coordinates, color themes, flow steps) for real-time rendering.

- **Live Device Context Awareness**
  Consumes real-time device context including installed application catalogs (`app_catalog`), active foreground applications (`active_package`), and screen accessibility node hierarchies (`ui_hierarchy`).

- **Resilient Multi-Tier Planning Engine**
  - **Primary:** Gemini API via the official `google-genai` SDK using structured JSON schema output and minimal-latency configurations.
  - **Failover:** Automatic model fallback (`gemini-3.5-flash-lite` -> `gemini-2.5-flash-lite` -> `gemini-2.5-flash`).
  - **Offline Heuristic Engine:** Comprehensive regex and rule-based fallback planner ensuring high availability even under network interruptions or quota limits.

---

## Project Structure

```
backend/
├── Dockerfile          # Production Docker configuration (Python 3.11-slim)
├── requirements.txt    # Project dependencies
├── main.py             # FastAPI entrypoint, middleware, routes, exception handlers
├── models.py           # Pydantic v2 data models, schemas, and action types
├── planner.py          # Gemini AI reasoning engine and deterministic planner
├── .env                # Local environment variables
└── README.md           # Documentation
```

---

## API Reference

### 1. Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "ok",
  "service": "The-Buddy-Planner",
  "model": "gemini-3.5-flash-lite"
}
```

---

### 2. Task Planning & Decomposition

**Endpoint:** `POST /api/v1/plan`

**Request Body (`PlanRequest`):**

| Field | Type | Required | Description |
|---|---|---|---|
| `user_prompt` | `string` | Yes | Voice transcript or text prompt from the user |
| `talk_mode` | `string` | No | Interaction mode (`COMMAND`, `CONVERSATION`) |
| `active_package` | `string` | No | Currently focused app package name |
| `app_catalog` | `AppCatalogEntry[]` | No | List of installed apps (`label`, `package_name`) |
| `ui_hierarchy` | `UiNodeSummary[]` | No | Visible screen elements (ID, text, bounds, clickable) |

**Sample Request (`TYPE_OS_ACTION`):**
```json
{
  "user_prompt": "Open YouTube and play Interstellar theme",
  "talk_mode": "COMMAND",
  "active_package": "com.android.launcher",
  "app_catalog": [
    {"label": "YouTube", "package_name": "com.google.android.youtube"},
    {"label": "WhatsApp", "package_name": "com.whatsapp"}
  ],
  "ui_hierarchy": []
}
```

**Sample Response (`TYPE_OS_ACTION`):**
```json
{
  "status": "ok",
  "mode": "TYPE_OS_ACTION",
  "original_prompt": "Open YouTube and play Interstellar theme",
  "speech_reply": "Opening YouTube and playing Interstellar Theme.",
  "steps": [
    {
      "step": 1,
      "action_type": "LAUNCH_INTENT",
      "target": "com.google.android.youtube",
      "payload": "Interstellar Theme",
      "confirmation_required": false
    }
  ],
  "canvas_draw_instructions": null
}
```

**Sample Response (`TYPE_CONVERSATION`):**
```json
{
  "status": "ok",
  "mode": "TYPE_CONVERSATION",
  "original_prompt": "Explain how transformer attention works",
  "speech_reply": "Here is how Transformer Attention works step by step on your visual canvas.",
  "steps": [],
  "canvas_draw_instructions": {
    "title": "Transformer Attention",
    "summary": "Interactive visual breakdown of Transformer Attention",
    "nodes": [
      {
        "id": "n1",
        "label": "1. Input & Trigger",
        "sublabel": "Initiate Transformer Attention",
        "shape": "ROUND_RECT",
        "x_ratio": 0.5,
        "y_ratio": 0.18,
        "color_hex": "#6366F1"
      },
      {
        "id": "n2",
        "label": "2. Core Mechanism",
        "sublabel": "State & Encoding",
        "shape": "CIRCLE",
        "x_ratio": 0.28,
        "y_ratio": 0.5,
        "color_hex": "#06B6D4"
      }
    ],
    "edges": [
      {
        "from_id": "n1",
        "to_id": "n2",
        "label": "Encode"
      }
    ],
    "flow_steps": [
      "Capture initial input for Transformer Attention",
      "Execute core mechanism & transformation",
      "Deliver verified output"
    ]
  }
}
```

---

## Supported Action Primitives

| Action Type | Target | Payload | Example Description |
|---|---|---|---|
| `LAUNCH_INTENT` | Package name (e.g. `com.google.android.youtube`) | Query or URI | Launch app or search deep link |
| `WHATSAPP_SEND` | Contact name or phone number | Message text | Compose and send messaging intent |
| `CLICK` | UI Node ID or text label | Target label | Accessibility click on screen element |
| `TYPE` | Input field identifier | Text to input | Enter text into focused edit field |
| `SCROLL` | Direction (`UP`, `DOWN`, `LEFT`, `RIGHT`) | Direction | Perform gesture scroll on active viewport |
| `SYSTEM_SETTING` | Setting name (`settings`, `wifi`, `bluetooth`) | Optional parameter | Open system settings panel |
| `SCREENSHOT` | `system` | None | Capture screen frame |
| `BACK` | `system` | None | Trigger system back navigation |
| `VERIFY_SUCCESS` | Condition identifier | Expected state | Validate screen state post-action |

---

## Installation & Setup

### Prerequisites

- Python 3.11+
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Set Up Virtual Environment

```bash
cd "backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Environment Configuration

Create or update `.env` in the backend root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
HOST=0.0.0.0
PORT=8000
```

### 3. Run the Development Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be accessible at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

---

## Docker Deployment

Build and run the containerized backend:

```bash
# Build Docker image
docker build -t the-buddy-backend .

# Run container with environment variables
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  --name the-buddy-backend \
  the-buddy-backend
```

# Explicandum Core (Brain)

The reasoning engine and backend for the Explicandum project. This FastAPI-based service orchestrates multi-agent logical and philosophical analysis using Google Gemini models.

## 🧠 Core Architecture

Explicandum Core follows a modular agentic design:

- **FastAPI Layer**: High-performance asynchronous API endpoints.
- **Agentic Engine**: Simulates specialized personas:
    - **Logic Analyst**: Focuses on premise verification, logical consistency, and fallacy detection.
    - **Philosophy Expert**: Connects discussions to epistemological and ontological frameworks.
- **RAG Integration**: Ready-to-use schemas for Retrieval-Augmented Generation.
- **Stance Extraction**: Automated identification of core user beliefs to maintain long-term consistency.

## 🛠 Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI Engine**: [Google Generative AI (Gemini)](https://ai.google.dev/)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Server**: Uvicorn

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- A Google AI Studio API Key

### Installation

1.  **Clone and enter the directory:**
    ```bash
    cd explicandum-core
    ```

2.  **Create a virtual environment:**
    ```bash
    uv venv --python 3.12

    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    uv pip install -r requirements.txt
    ```

4.  **Configuration:**
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    DATABASE_URL=sqlite:///./explicandum.db
    ```

5.  **Run the server:**
    ```bash
    uvicorn app.main:app --reload
    ```

The API will be available at `http://localhost:8000`. You can explore the interactive docs at `http://localhost:8000/docs`.

## 📡 API Endpoints

- `POST /chat`: Primary streaming endpoint for agentic reasoning.
- `POST /extract-stance`: Analyzes messages for philosophical stances.
- `GET /health`: System status check.

## 🔗 Related Repositories

- [Explicandum UI](https://github.com/zouzh14/explicandum-ui): The React-based investigator interface.

<!-- da4177ca-15a7-4065-878d-41b01e176ec7 92c6b203-3579-4a0d-8ef6-0f3985d8636e -->
# Reflexion Interviewer Implementation Plan

## Phase 1: Project Setup & Configuration

### 1.1 Initialize Project Structure

- Create directory structure: `backend/`, `frontend/`, `config/`, `utils/`, `models/`, `services/`
- Set up `requirements.txt` with: `fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `PyPDF2` or `pdfplumber`, `httpx`, `python-dotenv`
- Create `.env.example` for API keys and configuration
- Add `.gitignore` for Python/Node projects

### 1.2 Configure NVIDIA NIM API Access

- Set up environment variables for NVIDIA NIM API endpoints and keys
- Create `config/nvidia_config.py` for model endpoints:
- Nemotron-super-49b-v1_5 endpoint for main interview agent
- Nemotron-Nano-12B-v2-VL endpoint for resume analysis
- Implement API client wrapper in `services/nvidia_client.py`

## Phase 2: Backend Core Development

### 2.1 Resume Analysis Service

- Create `services/resume_analyzer.py`:
- PDF to image conversion for VL model
- Call Nemotron-Nano-12B-v2-VL via NIM API
- Parse and extract: skills, experience, education, projects
- Return structured candidate profile (JSON)

### 2.2 Interview Agent Core

- Create `services/interview_agent.py` (A.I. Harrison):
- Initialize with candidate profile and job description
- Implement multi-phase interview structure:
  - **Phase 1**: Warm-up & background questions
  - **Phase 2**: Technical depth (based on resume skills)
  - **Phase 3**: Problem-solving scenario
  - **Phase 4**: Behavioral & wrap-up
- State management for conversation history
- Dynamic question generation using Nemotron-super-49b-v1_5

### 2.3 Conversation Engine

- Create `services/conversation_engine.py`:
- Buil
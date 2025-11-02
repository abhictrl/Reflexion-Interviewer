# Reflexion Interviewer - Auto-Interviewer Agent

## Project Overview

The Reflexion Interviewer is an AI-powered autonomous interview agent designed to replace the static Online Assessment (OA) stage of the hiring process. Instead of traditional LeetCode problems or multiple-choice questions, this agent:

- **Analyzes candidate resumes** using the Nemotron-Nano-12B-v2-VL vision-language model
- **Conducts dynamic, multi-phase technical interviews** that feel like real conversations
- **Reasons and adapts** its questions in real-time based on candidate responses
- **Generates structured assessment reports** for hiring managers

The goal is to create a more realistic, fair, and effective screening tool that saves senior engineers' time while providing a better candidate experience.

## Architecture
<img width="1248" height="832" alt="Architectural Diagram Agentic Interviewer" src="https://github.com/user-attachments/assets/617393c7-eb41-40b9-8cb2-97d4e4ab9331" />

### Models Used

1. **Nemotron-Super-49B-v1_5**: Primary model for the main Interview Agent (A.I. Harrison)
   - Handles complex autonomous reasoning
   - Multi-step dialogue planning
   - Dynamic question generation

2. **Nemotron-Nano-12B-v2-VL**: Vision-Language Model for resume analysis
   - Processes resume PDFs as images
   - Extracts structured candidate data
   - Provides context for personalized interviews

## Project Structure

```
Reflexion Interviewer/
├── backend/          # FastAPI backend application
├── frontend/         # Minimal web interface
├── config/           # Configuration files
│   └── nvidia_config.py
├── services/         # Core business logic
│   ├── nvidia_client.py
│   ├── resume_analyzer.py
│   ├── interview_agent.py
│   ├── conversation_engine.py
│   └── assessment_engine.py
├── models/           # Pydantic data models
├── utils/            # Utility functions
├── venv/             # Virtual environment
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.9+ (tested with Python 3.13)
- NVIDIA API key for NIM (NVIDIA Inference Microservices)
- Virtual environment support
- Poppler-utils (for PDF processing)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - Windows: Install from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Reflexion-Interviewer"
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your NVIDIA API key:
   ```env
   NVIDIA_API_KEY=your_nvidia_api_key_here
   ```

### Running the Application

**Quick Start (Recommended):**
```bash
./run.sh
```

**Manual Start:**
```bash
source venv/bin/activate
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Access the application:**
- Frontend Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### Resume Upload
- `POST /api/upload-resume`: Upload candidate resume (PDF) and job description

### Interview Management
- `POST /api/start-interview`: Initialize interview session
- `POST /api/interview/message`: Send candidate response, receive next question
- `GET /api/interview/status`: Get current interview state

### Reports
- `GET /api/interview/report`: Generate final assessment report

## Development Status

**Phase 1: ✅ Complete** - Project Setup & Configuration
- ✅ Project structure initialized
- ✅ NVIDIA NIM API client configured
- ✅ Dependencies installed
- ✅ Virtual environment setup
- ✅ Configuration management

**Phase 2: ✅ Complete** - Backend Core Development
- ✅ Resume analysis service implemented
- ✅ Interview agent core (A.I. Harrison) implemented
- ✅ Conversation engine integrated
- ✅ Assessment & scoring engine implemented
- ✅ FastAPI endpoints created

**Phase 3: ✅ Complete** - Frontend Development
- ✅ Minimal web interface created
- ✅ UI/UX components implemented
- ✅ Chat interface with typing indicators
- ✅ Report visualization

**Phase 4: ⏳ Ready for Testing** - Integration & Testing
- ✅ End-to-end integration completed
- ⏳ End-to-end testing pending
- ⏳ Edge case handling refinement pending

**Phase 5: ✅ Complete** - Documentation & Deployment
- ✅ Basic documentation complete
- ⏳ Deployment preparation (planned for production)

## Configuration

All configuration is managed through environment variables in `.env`:

- `NVIDIA_API_KEY`: Your NVIDIA API key
- `NEMOTRON_SUPER_49B_ENDPOINT`: API endpoint for main interview agent
- `NEMOTRON_NANO_VL_ENDPOINT`: API endpoint for resume analysis
- `NEMOTRON_SUPER_49B_MODEL`: Model name for super agent
- `NEMOTRON_NANO_VL_MODEL`: Model name for VL analysis

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributors
Abhishek Rana [https://github.com/abhictrl]



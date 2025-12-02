# Quick Start Guide - Reflexion Interviewer

Get up and running with the Reflexion Interviewer in 5 minutes!

## Prerequisites Check

Ensure you have:
- ✅ Python 3.9+ installed
- ✅ Poppler installed (`brew install poppler` on macOS)
- ✅ NVIDIA API key from https://build.nvidia.com/

## Step-by-Step Setup

### 1. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 2. Configure API Key

```bash
# Create .env file from template
cp .env.example .env

# Edit .env and add your NVIDIA API key
nano .env  # or use your preferred editor
```

**Important:** Replace `your_nvidia_api_key_here` with your actual NVIDIA API key.

### 3. Start the Server

**Option A: Use the quick start script**
```bash
./run.sh
```

**Option B: Manual start**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the Application

Open your browser and navigate to:
```
http://localhost:8000
```

You should see the Reflexion Interviewer interface!

## First Interview Test

1. **Upload a Resume**
   - Click "Click to upload" or drag a PDF resume
   - Paste a job description in the text area

2. **Start the Interview**
   - Click "Start Interview"
   - Wait for A.I. Harrison to introduce himself

3. **Answer Questions**
   - Respond naturally to the interview questions
   - The AI will adapt based on your answers

4. **View Results**
   - After the interview completes, view your assessment report
   - See scores, strengths, and areas for improvement

## Troubleshooting

### "Poppler not found"
- macOS: `brew install poppler`
- Ubuntu: `sudo apt-get install poppler-utils`
- Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

### "NVIDIA_API_KEY is required"
- Make sure you created `.env` file
- Add your API key: `NVIDIA_API_KEY=your_actual_key_here`

### "Import errors"
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

### Port 8000 already in use
- Change port in `run.sh` or specify: `--port 8001`
- Update frontend `index.html` API_BASE URL if needed

### "404 Not Found" or "NVIDIA API error"
- Verify your NVIDIA API key is valid at https://build.nvidia.com/
- Check that the model names in your `.env` file are correct
- Try updating the endpoint URLs in `.env`:
  ```
  NEMOTRON_SUPER_49B_ENDPOINT=https://ai.api.nvidia.com/v1/chat/completions
  NEMOTRON_NANO_VL_ENDPOINT=https://ai.api.nvidia.com/v1/chat/completions
  ```
- Alternative endpoint to try:
  ```
  NEMOTRON_SUPER_49B_ENDPOINT=https://integrate.api.nvidia.com/v1/chat/completions
  ```
- Verify your API key has access to the Nemotron models
- Check NVIDIA's API documentation for current endpoint URLs

## Testing Without Real Resume

You can test with the API directly at:
```
http://localhost:8000/docs
```

The interactive API documentation lets you test endpoints without the UI.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the [API Documentation](http://localhost:8000/docs) for endpoint details
- Check the code structure to understand the implementation

## Need Help?

- Check logs in the terminal for detailed error messages
- Verify your NVIDIA API key is valid
- Ensure all dependencies are installed
- Try the `/health` endpoint: `curl http://localhost:8000/health`

Happy Interviewing! 🤖


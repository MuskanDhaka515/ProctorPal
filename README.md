# ProctorPal

ProctorPal is a voice-based AI assistant I built for a university testing center.

The idea came from my experience working in Testing Services at Rowan University. Students often have similar questions about testing hours, ID requirements, make-up exams, available appointments, cancellations, and other testing procedures.

I wanted to build something that could handle these routine requests through a natural voice conversation, while still keeping important booking rules controlled by the application rather than by the LLM.

ProctorPal can answer policy questions, check available exam slots, create and cancel bookings, and escalate a conversation when staff assistance is needed.

## How it works
### Architecture

**Browser / Microphone** → **Faster-Whisper** → **LLM Agent** → **Agent Tools** → **SQLite / Policy Search**

The agent's final response is returned to the browser and can be spoken using the browser's text-to-speech functionality.


The basic flow is:

1. **Speech-to-text** — The browser records the student's voice and sends the audio to the Flask backend. Faster-Whisper converts it into text.

2. **Agent reasoning** — Claude processes the conversation and decides whether it can answer directly or needs to use one of the available tools.

3. **Tool calling** — The agent currently has five tools:
   - `search_policies`
   - `check_availability`
   - `book_slot`
   - `cancel_booking`
   - `escalate_to_staff`

4. **Policy retrieval** — Testing-center information is stored in `data/faq.md`. I use TF-IDF retrieval to find relevant policy information when students ask questions about things like hours or ID requirements.

5. **Booking validation** — Booking restrictions are checked in Python rather than relying only on the model. This includes the 24-hour notice requirement, 30-day booking window, Sunday closure, slot capacity, and duplicate-booking checks.

6. **Voice response** — The final response can be spoken back to the student using the browser's speech synthesis.

The interface also shows the tool calls being made and updates the bookings table during the conversation. I found this especially useful while testing and debugging the agent.

## Example conversations

Some requests ProctorPal can handle:

> "What ID do I need for my exam?"

> "What are the testing center hours on Friday?"

> "Do you have anything available next Tuesday afternoon?"

> "Book my Statistics make-up exam for 2 PM."

> "I need to cancel my booking."

> "I need to speak with someone from the testing center."

The booking tools also reject requests that break the configured rules, such as trying to schedule an exam on Sunday.

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Flask application and API endpoints |
| `agent.py` | Claude agent, conversation loop, and tool calling |
| `tools.py` | Agent tools and booking validation |
| `knowledge.py` | Policy/FAQ retrieval |
| `stt.py` | Faster-Whisper speech-to-text |
| `db.py` | SQLite booking storage |
| `templates/index.html` | Voice and chat interface |
| `data/faq.md` | Sample testing-center policy information |
| `tests/` | Unit and API tests |
| `eval/run_eval.py` | Scripted conversation evaluation |
| `Dockerfile` | Container configuration |
| `.github/workflows/ci.yml` | CI/CD workflow |

## Tech stack

| Area | Technology |
| --- | --- |
| Backend | Python, Flask |
| LLM | Claude API |
| Speech-to-text | Faster-Whisper |
| Retrieval | TF-IDF, scikit-learn |
| Database | SQLite |
| Voice output | Browser Speech Synthesis API |
| Testing | Pytest |
| Containerization | Docker |
| CI/CD | GitHub Actions |
| Deployment setup | AWS EC2 |

## Running locally

### 1. Clone the repository

```bash
git clone https://github.com/MuskanDhaka515/ProctorPal.git
cd ProctorPal
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the API key

Copy `.env.example` to a new file named `.env`.

Then add your Anthropic API key:

```text
ANTHROPIC_API_KEY=your-key-here
```

The `.env` file is excluded from Git and should never be committed.

### 5. Start ProctorPal

```bash
python app.py
```

Open:

```text
http://localhost:8000
```

Chrome or Edge works best for the voice interface.

The first voice request can take longer because the Faster-Whisper model may need to be downloaded.

## Testing

I wrote automated tests for the main parts of the application, including:

- agent tool calling
- Flask API endpoints
- policy search
- availability checking
- booking and capacity rules
- duplicate-booking prevention
- invalid time validation
- cancellation
- unknown or invalid tool requests

Run the tests with:

```bash
pytest -v
```

Current local test result:

```text
13 passed
```

These tests use a fake LLM client where appropriate, so they can test the application logic without making an Anthropic API request.

## Agent evaluation

I also created a separate evaluation suite with 10 scripted conversations that run against the real agent.

```bash
python eval/run_eval.py
```

Current result:

```text
9/10 scenarios passed
```

The scenarios cover policy questions, availability, booking, cancellation, escalation, and off-topic requests.

This evaluation uses the real Claude API and is separate from the unit/API test suite.

## Docker

Build the image:

```bash
docker build -t proctorpal .
```

Run it:

```bash
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your-key-here \
  proctorpal
```

Then open:

```text
http://localhost:8000
```

## Deployment setup

The project includes a GitHub Actions workflow for testing and Docker-based deployment to AWS EC2.

The intended deployment flow is:

**Push to `main`** → **GitHub Actions** → **Run tests** → **Build Docker image** → **AWS EC2 deployment**


For EC2 deployment, the repository expects GitHub secrets for:

- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`

For a public voice demo, HTTPS is also required because browsers restrict microphone access on non-secure remote pages.

## A problem I ran into

While testing the voice workflow, transcription was failing even though the rest of the application was working.

I used the Flask logs to isolate the failure to the speech-to-text layer and found a compatibility issue between Faster-Whisper and the installed PyAV version.

Pinning the compatible PyAV dependency fixed the issue. I added that version to `requirements.txt` so a fresh installation uses the same working environment.

This was also a useful reminder of why I like keeping the different parts of the agent modular — it makes problems much easier to isolate.

## Notes

The policies in `data/faq.md` are sample data for a fictional testing center. They can be replaced with another organization's policies without changing the overall agent architecture.

ProctorPal is currently a functional prototype and is not connected to Rowan University's production systems or student data.

## What I want to add next

- Twilio Voice integration for real phone calls
- streaming transcription and responses
- calendar integration
- conversation analytics and monitoring
- more evaluation scenarios
- improved staff handoff workflow

## What I learned

The main thing I learned from this project is that building a useful AI agent involves more than getting an LLM to generate a good response.

The model needs clear tools, the application needs its own validation rules, and each part of the workflow needs to be observable enough to troubleshoot when something goes wrong.

That is the part of AI automation I enjoy most: connecting the model to real actions while keeping the workflow reliable and understandable.
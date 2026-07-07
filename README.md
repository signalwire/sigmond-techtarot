# SignalWire TechTarot

A mystical tarot reading application featuring Sigmond, an AI-powered tarot reader that provides three-card readings (Past, Present, Future) using a tech-themed tarot deck.

**Live demo:** https://techtarot.signalwire.me/

## Overview

This application combines SignalWire's AI Agent technology with WebRTC video calling to create an interactive tarot reading experience. Users connect via video call to Sigmond, who performs personalized tarot readings using a custom tech-themed deck.

## Features

- **AI-Powered Tarot Reader**: Sigmond uses ElevenLabs' Adam voice for a mystical experience
- **Three-Card Spread**: Traditional Past, Present, Future reading format
- **Tech-Themed Tarot Deck**: Custom deck featuring programming and technology concepts
- **Interactive Web Interface**: Real-time card display with flip animations
- **Video Call Integration**: Face-to-face readings via SignalWire WebRTC (the agent has vision enabled and greets you based on what it sees)
- **Zero-Config Auth**: Guest tokens are minted server-side via `/get_token` — no credentials in the frontend
- **Mute Controls**: Option to start muted or toggle mute during the call
- **Event Logging**: Optional debug log for monitoring call events

## Project Structure

```
techtarot/
├── app.py                              # AI agent + web server (single entry point)
├── signalwire_ai_knowledge_prompt.md   # SignalWire knowledge base for the agent
├── Procfile                            # Production start command (gunicorn)
├── requirements.txt / runtime.txt      # Python dependencies and version
├── app.json / CHECKS / .dokku/         # Dokku deployment configuration
├── .github/workflows/                  # Deploy + preview workflows (dokku-deploy-system)
├── scripts/                            # Deck generation tooling (not served)
└── web/                                # Public static root
    ├── index.html                      # Main UI
    ├── app.js                          # Frontend logic (@signalwire/js v4)
    ├── signalwire.js                   # SignalWire browser SDK build
    ├── card_images/                    # Tarot card images (Major, CloudDevelopers,
    │                                   #   Docker, FreeSWITCHDevs, Linux)
    ├── tarot_deck.json                 # Card definitions and meanings
    ├── sigmond_tarot_idle.mp4          # Dealer idle video
    ├── sigmond_tarot_talking.mp4       # Dealer talking video
    └── bgmusic.mp3                     # Background music
```

## How It Works

1. **User Connection**: Users click "Connect" — the frontend fetches a guest token and destination from `/get_token`, then dials the agent over WebRTC
2. **Agent Registration**: On startup, the app auto-registers an External SWML Handler named `$AGENT_NAME` with SignalWire, pointing at the app's `/swml` endpoint
3. **Introduction**: Sigmond takes a look at the seeker (vision), introduces himself, and explains the reading process
4. **Card Drawing**: When ready, Sigmond draws three cards using the `draw_cards` SWAIG function
5. **Visual Display**: Cards appear on screen with dealing animations, driven by SWML user events
6. **Interpretation**: Sigmond interprets each card considering its position (Past/Present/Future), upright or reversed orientation, and tech-themed symbolism

## Local Development

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure credentials:
   ```bash
   cp .env.example .env
   # Fill in SIGNALWIRE_SPACE_NAME, SIGNALWIRE_PROJECT_ID, SIGNALWIRE_TOKEN
   ```

3. For a full end-to-end call, SignalWire must be able to reach your machine — set `SWML_PROXY_URL_BASE` in `.env` to a public tunnel URL (e.g., ngrok):
   ```bash
   ngrok http 5000
   # SWML_PROXY_URL_BASE=https://xxxx.ngrok.io
   ```

4. Run the app:
   ```bash
   python app.py
   ```

5. Open http://localhost:5000/ and click Connect.

### Endpoints

| Path | Purpose |
|---|---|
| `/` | Web client (static files from `web/`) |
| `/get_token` | Mints a scoped guest token + destination address for the frontend |
| `/swml` | SWML endpoint the agent serves (basic auth) |
| `/health`, `/ready` | Health checks for deployment |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SIGNALWIRE_SPACE_NAME` | Yes | Your SignalWire space (`myspace` or `myspace.signalwire.com`) |
| `SIGNALWIRE_PROJECT_ID` | Yes | SignalWire project ID |
| `SIGNALWIRE_TOKEN` | Yes | SignalWire API token |
| `SWML_PROXY_URL_BASE` | Local only | Public URL base for SWML callbacks; in production `APP_URL` is set automatically by Dokku |
| `SWML_BASIC_AUTH_USER` / `SWML_BASIC_AUTH_PASSWORD` | Recommended in prod | Basic auth for the SWML endpoint (auto-generated per process if unset) |
| `AGENT_NAME` | No | SWML handler resource name (default `techtarot`; set automatically on Dokku) |
| `PORT` | No | Server port (default 5000) |
| `POST_PROMPT_URL` | No | Webhook to receive conversation summaries |

## Deployment

This repo deploys via the [signalwire-demos dokku-deploy-system](https://github.com/signalwire-demos/dokku-deploy-system) reusable workflows:

- Push to `main` → production at `https://techtarot.signalwire.me`
- Pull requests → preview apps at `https://techtarot-pr-<n>.signalwire.me`

App-specific configuration (the `SIGNALWIRE_*` variables above) lives in the repo's GitHub Environment variables; infrastructure secrets are provided at the org level. See the deploy-system docs for details.

## Tarot Deck

The tech-themed tarot deck includes:
- **Major Arcana**: Technology concepts like "The Debugger", "Lord of Legacy Code", "Infinite Loop"
- **Minor Arcana Suits**:
  - **Cloud Developers**: Representing ideas and communication
  - **Docker**: Representing emotions and containers
  - **FreeSWITCH Devs**: Representing material concerns
  - **Linux**: Representing action and energy

Each card includes upright and reversed meanings tailored to technology themes.

## Technical Details

- **AI Agent**: Python, built on the [SignalWire SDK](https://github.com/signalwire/signalwire-python) (`signalwire-sdk`) AgentBase/AgentServer
- **Frontend**: Vanilla JavaScript with the `@signalwire/js` v4 browser SDK
- **Voice**: ElevenLabs Adam voice for natural speech
- **SWML**: SignalWire Markup Language user events drive the card UI

## Learning Resources

- [SignalWire Python SDK (GitHub)](https://github.com/signalwire/signalwire-python) - Unified Python SDK for building AI agents
- [SignalWire AI Documentation](https://developer.signalwire.com/ai/) - AI Agent guides and tutorials
- [SWML Documentation](https://developer.signalwire.com/swml/) - SignalWire Markup Language reference
- [Browser SDK Documentation](https://developer.signalwire.com/sdks/browser-sdk/) - JavaScript SDK for WebRTC

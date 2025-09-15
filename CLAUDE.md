# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SignalWire TechTarot is an AI-powered mystical tarot reading application featuring Sigmond, a fortune teller that uses tech-themed tarot cards. The project demonstrates building sophisticated SignalWire AI Agents with integrated web serving, real-time video communication, and step-based conversation flow.

## Key Architecture Components

### Main Components
- **bot/sigmond_tarot_steps.py**: Core AI tarot reader agent using SignalWire Agents SDK - implements step-based conversation flow (greeting → card reading) with integrated web serving. Serves both API and web client from a single process on the same port.
- **web/client/**: Interactive web interface with mystical theme - handles WebRTC video calls and displays tarot cards
- **web/card_images/**: Tech-themed tarot deck organized by suits (Docker, Linux, FreeSWITCH Devs, Cloud Developers) plus Major Arcana cards
- **web/tarot_deck.json**: Complete card definitions with meanings and interpretations

### Conversation Flow Pattern
Step-based conversation management:
1. **initial_greeting**: Get visual input, greet seeker, wait for readiness
2. **card_reading**: Draw three cards (past/present/future), interpret meanings

### Authentication Model
- **Public Routes** (no auth): Web client, JavaScript files, card images, media files, favicon, OG images
- **Protected Routes** (requires Basic Auth): `/tarot`, `/tarot/swaig`, `/tarot/post_prompt`

## Development Commands

### Running the Application

#### Direct Python execution:
```bash
cd bot
python sigmond_tarot_steps.py  # Runs on port 5000 by default

# Or specify a custom port:
python sigmond_tarot_steps.py --port 8080

# The bot serves:
# - Web client at http://localhost:5000/
# - Card images at http://localhost:5000/card_images/
# - Media files (videos, audio) at root
# - SWML endpoint at http://localhost:5000/tarot (requires auth)
```

#### Using the Control Script:
```bash
cd bot
./bot.sh start    # Start on port 5000
./bot.sh stop     # Stop the tarot reader
./bot.sh restart  # Restart
./bot.sh status   # Check if running
./bot.sh logs     # View logs
```

### Deployment

#### Heroku/Dokku:
```bash
# The Procfile runs: python bot/sigmond_tarot_steps.py --port $PORT
git push dokku main  # For Dokku
git push heroku main # For Heroku
```

### Testing
```bash
# Test SWAIG functions
cd bot
swaig-test sigmond_tarot_steps.py --list-tools
swaig-test sigmond_tarot_steps.py --exec draw_cards

# Local testing
python sigmond_tarot_steps.py
# Open browser to http://localhost:5000
# Check API: curl -u username:password http://localhost:5000/tarot
```

## Environment Variables

**Optional:**
- `TAROT_WEB_ROOT`: URL where media files are hosted (defaults to `http://localhost:{port}`)
- `PORT`: Port to run the service on (default: 5000, used by Heroku/Dokku)
- `SWML_DEV_USERNAME`: Basic auth username for API (auto-generated if not set)
- `SWML_DEV_PASSWORD`: Basic auth password for API (auto-generated if not set)

**For HTTPS:**
- `SWML_SSL_ENABLED=true`
- `SWML_SSL_CERT_PATH=/path/to/cert.pem`
- `SWML_SSL_KEY_PATH=/path/to/key.pem`
- `SWML_DOMAIN=yourdomain.com`

## Key Implementation Patterns

### SWAIG URL Override
The `_build_webhook_url` method is overridden to ensure all SWAIG function URLs include the `/tarot` prefix when the agent is mounted at that path.

### Step Transitions
```python
.set_step_criteria("The user's response contains any form of affirmation")
.set_valid_steps(["card_reading"])
```

### Visual Input Integration
The agent uses `get_visual_input` function to see the user and incorporate their appearance into the greeting.

### Card Drawing Logic
- Uses cryptographically secure random selection
- Three-card spread: Past, Present, Future
- Each card can be upright or reversed
- Comprehensive interpretations from tarot_deck.json

## Important Files to Modify

When updating the application:
1. **bot/sigmond_tarot_steps.py**: Main agent logic, conversation flow, integrated web serving
2. **web/client/index.html**: UI structure and Open Graph meta tags
3. **web/client/app.js**: Frontend JavaScript, WebRTC handling, card display logic
4. **web/tarot_deck.json**: Card definitions and meanings

## Tech-Themed Tarot Suits

- **Docker** (Cups equivalent): Emotions, containers, isolation
- **Linux** (Wands equivalent): Creativity, open source, freedom
- **FreeSWITCH Devs** (Swords equivalent): Communication, logic, protocols
- **Cloud Developers** (Pentacles equivalent): Material world, infrastructure, resources
- **Major Arcana**: Tech-themed archetypal cards (The Noob, The Debugger, etc.)

## Testing Checklist

Before deploying:
1. Verify step transitions work correctly
2. Test card drawing returns valid cards
3. Check SWML events update the UI
4. Ensure authentication only applies to /tarot endpoints
5. Verify static files load without auth
6. Test SWAIG functions are called at correct URLs
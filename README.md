# SignalWire Tarot Reading Application

A mystical tarot reading application featuring Sigmond, an AI-powered tarot reader that provides three-card readings (Past, Present, Future) using a tech-themed tarot deck.

## Overview

This application combines SignalWire's AI Agent technology with WebRTC video calling to create an interactive tarot reading experience. Users connect via video call to Sigmond, who performs personalized tarot readings using a custom tech-themed deck.

## Features

- **AI-Powered Tarot Reader**: Sigmond uses ElevenLabs' Adam voice for a mystical experience
- **Three-Card Spread**: Traditional Past, Present, Future reading format
- **Tech-Themed Tarot Deck**: Custom deck featuring programming and technology concepts
- **Interactive Web Interface**: Real-time card display with flip animations
- **Video Call Integration**: Face-to-face readings via SignalWire WebRTC
- **Mute Controls**: Option to start muted or toggle mute during the call
- **Event Logging**: Optional debug log for monitoring call events

## Project Structure

```
tarot/
├── signalwire-agents/     # Bot implementation
│   └── sigmond_tarot.py   # Main AI agent
├── web/                   # Web interface
│   ├── client/            # Frontend application
│   │   ├── index.html     # Main UI
│   │   ├── app.js         # JavaScript logic
│   │   └── signalwire.js  # SignalWire SDK
│   ├── card_images/       # Tarot card images
│   │   ├── Major/         # Major Arcana cards
│   │   ├── CloudDevelopers/
│   │   ├── Docker/
│   │   ├── FreeSWITCHDevs/
│   │   ├── Linux/
│   │   └── tarot_back.jpg # Card back design
│   └── tarot_deck.json    # Card definitions and meanings
└── README.md              # This file
```

## Setup

### Bot Setup

1. Navigate to the bot directory:
   ```bash
   cd signalwire-agents
   ```

2. Install dependencies:
   ```bash
   pip install signalwire-agents
   ```

3. Run Sigmond:
   ```bash
   python sigmond_tarot.py --port 3000
   ```

### Web Interface Setup

1. Update the SignalWire token in `web/client/app.js`:
   ```javascript
   const STATIC_TOKEN = 'YOUR_SIGNALWIRE_TOKEN_HERE';
   ```

2. Serve the web directory using any web server:
   ```bash
   cd web
   python -m http.server 8080
   ```

3. Access the application at `http://localhost:8080/client/`

## How It Works

1. **User Connection**: Users click "Connect to Sigmond" to initiate a video call
2. **Introduction**: Sigmond introduces himself and explains the reading process
3. **Card Drawing**: When ready, Sigmond draws three cards using the `draw_cards` function
4. **Visual Display**: Cards appear on screen with dealing animations
5. **Interpretation**: Sigmond interprets each card considering:
   - Card position (Past/Present/Future)
   - Upright or reversed orientation
   - Tech-themed symbolism
6. **Interactive Elements**: Users can click cards to flip them back and forth

## Tarot Deck

The tech-themed tarot deck includes:
- **Major Arcana**: Technology concepts like "The Debugger", "Lord of Legacy Code", "Infinite Loop"
- **Minor Arcana Suits**:
  - **Cloud Developers**: Representing ideas and communication
  - **Docker**: Representing emotions and containers
  - **FreeSWITCH Devs**: Representing material concerns
  - **Linux**: Representing action and energy

Each card includes upright and reversed meanings tailored to technology themes.

## Configuration

- **Bot Port**: Configure with `--port` flag (default: 3000)
- **Base URL**: Update `BASE_URL` in app.js for card image paths
- **Destination**: Update `DESTINATION` in app.js for SignalWire routing

## Features in Detail

### Mute Functionality
- Checkbox to start calls muted
- Toggle mute button during calls
- Uses native WebRTC audio track control

### Event Logging
- Optional debug log checkbox
- Shows SignalWire events and user interactions
- Collapsible interface

### Card Display
- Automatic card flipping after dealing
- Click cards to toggle between front and back
- Reversed cards display upside-down
- Smooth animations and transitions

## Technical Details

- **SignalWire SDK**: Uses Fabric API for WebRTC connections
- **AI Agent**: Python-based using SignalWire Agents framework
- **Voice**: ElevenLabs Adam voice for natural speech
- **SWML**: SignalWire Markup Language for user events
- **Frontend**: Vanilla JavaScript with responsive CSS
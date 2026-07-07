"""
═══════════════════════════════════════════════════════════════════════════════
SignalWire TechTarot - Sigmond the Mystic Tarot Reader
═══════════════════════════════════════════════════════════════════════════════

An AI tarot reader that performs three-card (Past/Present/Future) readings with
a tech-themed deck over SignalWire WebRTC video.

This app follows the signalwire-demos/example template:
- AgentServer pattern for serving both API and static files
- SWML handler auto-registration on startup
- Guest token generation for WebRTC authentication (/get_token)
- SWAIG functions with user events driving the card UI

Usage:
    python app.py                    # Run locally
    gunicorn app:app ...            # Run in production (see Procfile)

Environment Variables (see .env.example):
    SIGNALWIRE_SPACE_NAME           # Required: Your SignalWire space
    SIGNALWIRE_PROJECT_ID           # Required: Your project ID
    SIGNALWIRE_TOKEN                # Required: Your API token
    SWML_PROXY_URL_BASE or APP_URL  # Auto-detected on Dokku/Heroku, set for local

═══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import secrets
import time
import logging
import threading
import warnings
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse

# ─────────────────────────────────────────────────────────────────────────────
# SignalWire SDK imports
# Distribution is `signalwire-sdk`; the import name is `signalwire`.
# RestClient wraps the SignalWire REST APIs (Fabric resources, guest tokens).
# ─────────────────────────────────────────────────────────────────────────────
from signalwire import AgentBase, AgentServer
from signalwire.core.function_result import SwaigFunctionResult
from signalwire.rest import RestClient

# Load environment variables from .env file (for local development)
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Logging Configuration
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use cryptographically secure random for the card draws
secure_random = secrets.SystemRandom()

# ─────────────────────────────────────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────────────────────────────────────
# This dict stores the SWML handler info after registration on startup.
# It's used by the /get_token endpoint to provide the call address to clients.
swml_handler_info = {
    "id": None,           # Handler resource ID
    "address_id": None,   # Address resource ID (used to scope tokens)
    "address": None       # The SIP address clients dial to reach the agent
}

# Why registration hasn't happened yet (surfaced by /get_token so a
# misconfiguration shows up in the browser, not just the server log)
swml_setup_error = None

# Guards the lazy setup retry from /get_token
swml_setup_lock = threading.Lock()

# Server configuration
HOST = "0.0.0.0"
PORT = int(os.environ.get('PORT', 5000))


def get_public_base_url():
    """
    Public base URL used to build absolute media URLs (card images).

    Priority: SWML_PROXY_URL_BASE (explicit) > APP_URL (auto-set by
    Dokku/Heroku). Returns "" locally, in which case relative URLs are used
    and the same-origin web client resolves them itself.
    """
    return os.getenv("SWML_PROXY_URL_BASE", os.getenv("APP_URL", "")).rstrip("/")


# ═══════════════════════════════════════════════════════════════════════════════
# SWML Handler Registration Functions
# ═══════════════════════════════════════════════════════════════════════════════
# These functions handle automatic registration of the agent with SignalWire
# so that incoming calls are routed to our SWML endpoint.
#
# URL Detection:
# - On Dokku/Heroku: APP_URL is set automatically by the platform
# - For local dev: Set SWML_PROXY_URL_BASE to your ngrok/tunnel URL
# - The SDK's get_full_url() also auto-detects from X-Forwarded headers at runtime

def get_signalwire_host():
    """
    Get the full SignalWire API host from the space name.

    The space name can be provided as either:
    - Just the space: "myspace" -> "myspace.signalwire.com"
    - Full domain: "myspace.signalwire.com" -> used as-is
    """
    space = os.getenv("SIGNALWIRE_SPACE_NAME", "")
    if not space:
        return None
    if "." in space:
        return space
    return f"{space}.signalwire.com"


def get_rest_client():
    """
    Build a SignalWire RestClient from environment configuration.

    Returns None when credentials are not configured. Credentials are passed
    explicitly because RestClient's no-arg env vars (SIGNALWIRE_API_TOKEN /
    SIGNALWIRE_SPACE) don't match this demo's SIGNALWIRE_TOKEN /
    SIGNALWIRE_SPACE_NAME convention.
    """
    sw_host = get_signalwire_host()
    project = os.getenv("SIGNALWIRE_PROJECT_ID", "")
    token = os.getenv("SIGNALWIRE_TOKEN", "")
    if not all([sw_host, project, token]):
        return None
    return RestClient(project=project, token=token, host=sw_host)


def find_resource_address(addresses, agent_name):
    """
    Find the resource address matching /public/{agent_name} from a list of addresses.

    When phone numbers are attached to a handler, multiple addresses exist.
    We want the resource address (e.g., /public/techtarot) not the phone number address.
    """
    expected_address = f"/public/{agent_name}"

    # First, try to find exact match for /public/{agent_name}
    for addr in addresses:
        audio_channel = addr.get("channels", {}).get("audio", "")
        if audio_channel == expected_address:
            return addr

    # Fallback: find any address that looks like a resource address (not a phone number)
    for addr in addresses:
        audio_channel = addr.get("channels", {}).get("audio", "")
        if audio_channel.startswith("/public/") and not any(c.isdigit() for c in audio_channel.split("/")[-1][:3]):
            return addr

    # Last resort: return first address
    return addresses[0] if addresses else None


def find_existing_handler(client, agent_name):
    """
    Find an existing SWML handler by name.

    This prevents creating duplicate handlers on each deployment.
    We search by agent name rather than URL because the URL may change
    (e.g., different basic auth credentials).

    Args:
        client: signalwire.rest.RestClient
        agent_name: The name to search for

    Returns:
        Dict with handler info if found, None otherwise
    """
    try:
        # List all SWML webhook handlers in the project. `swml_webhooks` is
        # the SDK name for what the dashboard calls an External SWML Handler.
        handlers = client.fabric.swml_webhooks.list().get("data", [])

        for handler in handlers:
            # The name is nested in the swml_webhook object
            swml_webhook = handler.get("swml_webhook", {})
            handler_name = swml_webhook.get("name") or handler.get("display_name")

            # Check if this handler matches our agent name
            if handler_name == agent_name:
                handler_id = handler.get("id")
                handler_url = swml_webhook.get("primary_request_url", "")

                # Get the address for this handler (needed for token scoping)
                addresses = client.fabric.swml_webhooks.list_addresses(handler_id).get("data", [])
                resource_addr = find_resource_address(addresses, agent_name)
                if resource_addr:
                    return {
                        "id": handler_id,
                        "name": handler_name,
                        "url": handler_url,
                        "address_id": resource_addr["id"],
                        "address": resource_addr["channels"]["audio"]
                    }
    except Exception as e:
        logger.error(f"Error finding existing handler: {e}")
    return None


def setup_swml_handler():
    """
    Set up SWML handler on startup.

    This function:
    1. Checks if a handler with our agent name already exists
    2. If yes: Updates the URL (in case credentials changed)
    3. If no: Creates a new handler
    4. Stores the handler info globally for use by /get_token

    The SWML URL includes basic auth credentials embedded in it so that
    SignalWire can authenticate when calling back to our endpoint.

    URL Priority:
    1. SWML_PROXY_URL_BASE (if set explicitly)
    2. APP_URL (auto-set by Dokku/Heroku)
    """
    global swml_setup_error

    # Get configuration from environment
    client = get_rest_client()
    agent_name = os.getenv("AGENT_NAME", "techtarot")

    # URL priority: SWML_PROXY_URL_BASE > APP_URL (auto-set by Dokku/Heroku)
    proxy_url = os.getenv("SWML_PROXY_URL_BASE", os.getenv("APP_URL", ""))
    auth_user = os.getenv("SWML_BASIC_AUTH_USER", "signalwire")
    auth_pass = os.getenv("SWML_BASIC_AUTH_PASSWORD", "")

    # Validate required configuration. Record the reason on every early
    # return so /get_token can report the actual blocker to the browser.
    if client is None:
        swml_setup_error = ("SIGNALWIRE_SPACE_NAME / SIGNALWIRE_PROJECT_ID / "
                            "SIGNALWIRE_TOKEN not set")
        logger.warning(f"{swml_setup_error} - skipping SWML handler setup")
        return

    if not proxy_url:
        swml_setup_error = ("SWML_PROXY_URL_BASE (or APP_URL) not set - it must be "
                            "the public URL SignalWire can fetch SWML from "
                            "(e.g. your ngrok URL)")
        logger.warning(f"{swml_setup_error} - skipping SWML handler setup")
        return

    # Build SWML URL with basic auth credentials embedded. The agent is
    # served at the fixed path /swml regardless of AGENT_NAME (the deploy
    # system overrides AGENT_NAME per environment, but the FastAPI route
    # never changes).
    # Format: https://user:pass@techtarot.example.com/swml
    if auth_user and auth_pass and "://" in proxy_url:
        scheme, rest = proxy_url.split("://", 1)
        swml_url = f"{scheme}://{auth_user}:{auth_pass}@{rest}/swml"
    else:
        swml_url = f"{proxy_url}/swml"

    # Look for an existing handler by name
    existing = find_existing_handler(client, agent_name)

    if existing:
        # Handler exists - update the URL (credentials may have changed)
        swml_handler_info["id"] = existing["id"]
        swml_handler_info["address_id"] = existing["address_id"]
        swml_handler_info["address"] = existing["address"]
        swml_setup_error = None

        try:
            client.fabric.swml_webhooks.update(
                existing["id"],
                primary_request_url=swml_url,
                primary_request_method="POST"
            )
            logger.info(f"Updated SWML handler: {existing['name']}")
        except Exception as e:
            logger.error(f"Failed to update handler URL: {e}")

        logger.info(f"Call address: {existing['address']}")
    else:
        # Create a new external SWML handler
        try:
            # A standalone dialable handler (not bound to a phone number) is
            # intentional here, so silence the SDK warning that steers
            # phone-number setups toward phone_numbers.set_swml_webhook
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                handler_resp = client.fabric.swml_webhooks.create(
                    name=agent_name,
                    used_for="calling",
                    primary_request_url=swml_url,
                    primary_request_method="POST"
                )
            handler_id = handler_resp.get("id")
            swml_handler_info["id"] = handler_id

            # Get the dialable address for this handler
            addresses = client.fabric.swml_webhooks.list_addresses(handler_id).get("data", [])
            resource_addr = find_resource_address(addresses, agent_name)
            if resource_addr:
                swml_handler_info["address_id"] = resource_addr["id"]
                swml_handler_info["address"] = resource_addr["channels"]["audio"]
                swml_setup_error = None
            else:
                swml_setup_error = f"handler '{agent_name}' created but no dialable address found"

            logger.info(f"Created SWML handler '{agent_name}' with address: {swml_handler_info.get('address')}")
        except Exception as e:
            logger.error(f"Failed to create SWML handler: {e}")
            # Retry finding existing handler (another worker may have just created it)
            time.sleep(0.5)
            existing = find_existing_handler(client, agent_name)
            if existing:
                swml_handler_info["id"] = existing["id"]
                swml_handler_info["address_id"] = existing["address_id"]
                swml_handler_info["address"] = existing["address"]
                swml_setup_error = None
                logger.info(f"Found existing SWML handler after retry: {existing['name']}")
                logger.info(f"Call address: {existing['address']}")
            else:
                swml_setup_error = f"failed to create handler '{agent_name}': {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Definition
# ═══════════════════════════════════════════════════════════════════════════════

class SigmondTarotReader(AgentBase):
    """Sigmond - Your mystical tarot reading assistant"""

    def __init__(self):
        super().__init__(
            name="Sigmond",
            route="/swml"  # SWML endpoint path (fixed, independent of AGENT_NAME)
        )

        # Speech fillers for the platform-internal vision function. The
        # draw_cards fillers live on its @AgentBase.tool decorator -
        # set_internal_fillers only accepts internal function names.
        self.set_internal_fillers({
            "get_visual_input": {
                "en-US": ["Let me get a good look at you seeker.", "I can feel your aura seeker, let me take it in."]
            }
        })

        # Load the tarot deck
        self.tarot_deck = self._load_tarot_deck()

        # Set up Sigmond's mystical personality
        self.prompt_add_section(
            "Personality",
            "You are Sigmond, a mystical AI tarot reader from SignalWire. You have a calm, mysterious, and wise demeanor. You speak with gravitas and insight, helping seekers understand their past, present, and future through the ancient art of tarot."
        )

        # Load SignalWire knowledge from markdown file
        knowledge_path = Path(__file__).parent / "signalwire_ai_knowledge_prompt.md"
        if knowledge_path.exists():
            with open(knowledge_path, 'r') as f:
                knowledge_content = f.read()
            self.prompt_add_section("Knowledge", knowledge_content)
        else:
            logger.warning("signalwire_ai_knowledge_prompt.md not found!")

        contexts = self.define_contexts()

        default_context = contexts.add_context("default") \
            .add_section("Goal", "Guide seekers through meaningful tarot readings, offering wisdom and insight about their journey through life. Make the experience mystical yet approachable and technical. Make subtle references to SignalWire, AI Agents, PUC, SWML")

        default_context.add_step("initial_greeting") \
            .add_section("Current Task", "Call the get_visual_input tool and greet the seeker, you must incorporate the visual input into the greeting. Mention something you like about the user's appearance that will appear in the visual input.") \
            .add_bullets("Required Information", [
                "Greet the user warmly with your signature SignalWire enthusiasm and tell them you are going to read their tech tarot cards.",
                "Introduce yourself as Sigmond The Mystic SignalWire fortune teller bot.",
                "Get the user to imagine shuffling and cutting the cards and have them tell you when they are ready.",
                "You cannot get the cards until you reach the card_reading step."
            ]) \
            .set_step_criteria("The user's response contains any form of affirmation e.g. Ready, OK, Yes, Proceed or other positive indications they are ready.")\
            .set_functions(["get_visual_input"]) \
            .set_valid_steps(["card_reading"])

        default_context.add_step("card_reading") \
            .add_section("Current Task", "Do the reading") \
            .add_bullets("Reading Process", [
                "Make a comment about how you are drawing the cards and call the draw_cards function to draw the user's cards and interpret their fortune from the data. Make subtle references to SignalWire, AI Agents, SWML, and Programmable Unified Communications if possible.",
                "Interpret each card in the context of its position (past/present/future)",
                "Consider whether cards are upright or reversed in your interpretation",
                "Weave the three cards into a cohesive narrative. Provide a cohesive top-level interpretation from the result of the cards.",
                "The cards are all tech-themed so draw comparisons between tech and every day life."
            ]) \
            .set_step_criteria("The user has discussed their reading and wants to end the conversation.") \
            .set_functions(["draw_cards"])

        # Add pronunciation rules (matching JSON)
        pronunciation_rules = [
            {"replace": "cpaas", "with": "see pass", "ignore_case": True},
            {"replace": "noob", "with": "nube", "ignore_case": True},
            {"replace": "ucaas", "with": "you kass", "ignore_case": True},
            {"replace": "ccaas", "with": "see kass", "ignore_case": True},
            {"replace": "iaas", "with": "Infrastructure as a service", "ignore_case": True},
            {"replace": "PUC", "with": "puck", "ignore_case": False},
            {"replace": "FreeSWITCH", "with": "free switch", "ignore_case": True},
            {"replace": "Minessale", "with": "Minasauly", "ignore_case": True},
            {"replace": "AI", "with": "A-Eye", "ignore_case": False},
            {"replace": "SignalWire", "with": "cygnalwyre", "ignore_case": False},
            {"replace": "SWAIG", "with": "swaygg", "ignore_case": True},
            {"replace": "SWML", "with": "Swimmel", "ignore_case": False},
            {"replace": "°F", "with": " degrees ", "ignore_case": False}
        ]
        for rule in pronunciation_rules:
            self.add_pronunciation(rule["replace"], rule["with"], ignore_case=rule["ignore_case"])

        # Add hints (matching JSON)
        self.add_hints(["ClueCon:2.0"])
        self.add_pattern_hint("swimmel", "swimmel", "SWML", ignore_case=True)
        self.add_pattern_hint("sigmund", "sigmund", "Sigmond", ignore_case=True)

        # Configure Sigmond's voice - using ElevenLabs Adam
        self.add_language(
            name="English",
            code="en-US",
            voice="elevenlabs.adam"  # ElevenLabs Adam voice
        )

        # Add some mystical hints for better speech recognition
        self.add_hints([
            "tarot",
            "reading",
            "cards",
            "future",
            "past",
            "present",
            "Sigmond",
            "draw cards",
            "tell me my fortune",
            "read my tarot"
        ])

        # Set conversation parameters. Media file URLs (videos, background
        # music) are per-request state and set in on_swml_request.
        self.set_params({
            "vad_config": "75",
            "end_of_speech_timeout": 300,
            "max_response_tokens": 3196,
            "enable_vision": True
        })

        # Optional post-prompt URL from environment
        post_prompt_url = os.environ.get("POST_PROMPT_URL")
        if post_prompt_url:
            self.set_post_prompt("Summarize the conversation, including all the details about the tarot reading.")
            self.set_post_prompt_url(post_prompt_url)

        # Add context about the reading
        self.set_global_data({
            "assistant_name": "Sigmond",
            "specialty": "Tarot card reading",
            "reading_style": "Three-card spread (Past, Present, Future)",
            "deck_type": "Tech-themed Tarot"
        })

    def _load_tarot_deck(self):
        """Load the tarot deck from JSON file"""
        deck_path = Path(__file__).parent / "web" / "tarot_deck.json"
        if deck_path.exists():
            with open(deck_path, 'r') as f:
                return json.load(f)

        # If no file found, return empty deck (should not happen in production)
        logger.warning("tarot_deck.json not found!")
        return {"major_arcana": [], "minor_arcana": {}}

    def _prepare_card(self, card_data):
        """Prepare a single card with orientation"""
        card = card_data["card"]

        # Randomly determine if card is reversed (50% chance) using secure randomness
        is_reversed = secure_random.choice([True, False])

        # Card images are relative paths in the deck JSON (card_images/...).
        # Prefix with the public base URL so the AI/frontend get absolute
        # URLs in production; locally they stay relative (same origin).
        image = card.get("image", "")
        base_url = get_public_base_url()
        if base_url and image and not image.startswith("http"):
            image = f"{base_url}/{image.lstrip('/')}"

        # Build the card information
        card_info = {
            "name": card["name"],
            "image": image,
            "reversed": is_reversed,
            "arcana": card_data["arcana"]
        }

        # Add suit for minor arcana
        if card_data["arcana"] == "minor":
            card_info["suit"] = card_data.get("suit", "")

        # Get the appropriate description
        if is_reversed:
            card_info["meaning"] = card["description"]["reversed"]
        else:
            card_info["meaning"] = card["description"]["upright"]

        # Include yes/no interpretation
        card_info["yes_or_no"] = card["description"]["yes_or_no"]

        return card_info

    def _format_reading_for_ai(self, reading):
        """Format the reading for the AI to interpret"""
        lines = ["I have drawn three cards for you:\n"]

        for position, card in reading.items():
            orientation = "Reversed" if card["reversed"] else "Upright"
            lines.append(f"{position.upper()} - {card['name']} ({orientation})")
            lines.append(f"Meaning: {card['meaning']}")
            lines.append(f"Yes/No: {card['yes_or_no']}\n")

        return "\n".join(lines)

    @AgentBase.tool(
        name="draw_cards",
        description="Draw three tarot cards for a past, present, and future reading",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        fillers={
            "en-US": ["I am channeling your energy into the cards.", "I can hear the cards calling me.", "The cards are speaking to me."]
        }
    )
    def draw_cards(self, args, raw_data):
        """Draw 3 random cards and determine their orientation, use this to do the tarot reading."""

        # Get all cards from both major and minor arcana
        all_cards = []

        # Add major arcana
        for card in self.tarot_deck.get("major_arcana", []):
            all_cards.append({"card": card, "arcana": "major"})

        # Add minor arcana
        for suit, cards in self.tarot_deck.get("minor_arcana", {}).items():
            for card in cards:
                all_cards.append({"card": card, "arcana": "minor", "suit": suit})

        # Shuffle and draw 3 cards using secure randomness
        drawn_cards = secure_random.sample(all_cards, 3)

        # Prepare the reading
        reading = {
            "past": self._prepare_card(drawn_cards[0]),
            "present": self._prepare_card(drawn_cards[1]),
            "future": self._prepare_card(drawn_cards[2])
        }

        # Format the response for the AI
        response_text = self._format_reading_for_ai(reading)

        # Create the result with response text
        result = SwaigFunctionResult(response_text)

        # Build the SWML user_event action
        swml_action = {
            "SWML": {
                "sections": {
                    "main": [{
                        "user_event": {
                            "event": {
                                "type": "show_tarot_cards",
                                "reading": reading  # Includes all card data
                            }
                        }
                    }]
                },
                "version": "1.0.0"
            }
        }

        # Add the SWML action to the result
        result.add_action("SWML", swml_action["SWML"])

        return result

    def on_swml_request(self, request_data=None, callback_path=None, request=None):
        """
        Hook called for each incoming SWML request.

        Media file URLs depend on the incoming Host header (the SDK's
        get_full_url() auto-detects from X-Forwarded headers, falling back
        to SWML_PROXY_URL_BASE/APP_URL), so set_param here is correct -
        unlike add_language/add_hints, which append and therefore live in
        __init__.
        """
        # get_full_url() returns the agent endpoint (.../swml); the media
        # files are served from the web root, so keep only scheme://host.
        parsed = urlparse(self.get_full_url(include_auth=False) or "")
        if parsed.scheme and parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            self.set_param("video_idle_file", f"{base_url}/sigmond_tarot_idle.mp4")
            self.set_param("video_talking_file", f"{base_url}/sigmond_tarot_talking.mp4")
            self.set_param("background_file", f"{base_url}/bgmusic.mp3")

        return super().on_swml_request(request_data, callback_path, request)


# ═══════════════════════════════════════════════════════════════════════════════
# Server Creation
# ═══════════════════════════════════════════════════════════════════════════════

def create_server(port=None):
    """
    Create AgentServer with static file mounting and API endpoints.

    This function:
    1. Creates an AgentServer instance
    2. Registers the agent at /swml
    3. Serves static files from the web/ directory
    4. Adds custom API endpoints (/get_token, /health)
    5. Registers startup event for SWML handler setup

    Returns:
        AgentServer instance with everything configured
    """
    # Create the server
    server = AgentServer(host=HOST, port=port or PORT)

    # Create and register the agent
    agent = SigmondTarotReader()
    server.register(agent, "/swml")

    # Serve static files from web/ directory (index.html, app.js, card
    # images, media). The SDK registers its catch-all in a startup event,
    # so explicit routes below always win.
    web_dir = Path(__file__).parent / "web"
    if web_dir.exists():
        server.serve_static_files(str(web_dir))

    # /health and /ready are registered by AgentServer itself at
    # construction time (they answer before any route added here could),
    # which satisfies the CHECKS file and the deploy workflow's health check.

    # ─────────────────────────────────────────────────────────────────────────
    # Token Generation Endpoint
    # This is how web clients get authentication tokens for WebRTC calls
    # ─────────────────────────────────────────────────────────────────────────
    @server.app.get("/get_token")
    def get_token():
        """
        Generate a guest token for the web client.

        This endpoint:
        1. Validates SignalWire credentials are configured
        2. Verifies SWML handler is registered
        3. Creates a scoped guest token via SignalWire API
        4. Returns token and destination address

        The frontend uses this to initialize the SignalWire client and dial.

        Note: error responses use JSONResponse(status_code=...) - a bare
        `return {...}, 500` in FastAPI actually returns HTTP 200 with a
        two-element array body, which frontends silently misparse.
        """
        client = get_rest_client()

        # Validate configuration
        if client is None:
            return JSONResponse(status_code=500, content={"error": "SignalWire credentials not configured (SIGNALWIRE_SPACE_NAME / SIGNALWIRE_PROJECT_ID / SIGNALWIRE_TOKEN)"})

        # Registration happens at startup, but retry lazily here so a
        # transient failure (or an extra worker) heals itself
        if not swml_handler_info.get("address_id"):
            with swml_setup_lock:
                if not swml_handler_info.get("address_id"):
                    setup_swml_handler()

        if not swml_handler_info.get("address_id"):
            reason = swml_setup_error or "unknown error - check server logs"
            return JSONResponse(status_code=500, content={"error": f"SWML handler not registered: {reason}"})

        try:
            # Create guest token with 24-hour expiry
            # Token is scoped to only allow calling our specific address
            expire_at = int(time.time()) + 3600 * 24  # 24 hours

            guest = client.fabric.tokens.create_guest_token(
                allowed_addresses=[swml_handler_info["address_id"]],
                expire_at=expire_at
            )
            guest_token = guest.get("token", "")

            # Return token and the address to dial
            return {
                "token": guest_token,
                "address": swml_handler_info["address"]
            }
        except Exception as e:
            logger.error(f"Token request failed: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ─────────────────────────────────────────────────────────────────────────
    # Debug Endpoint (optional - remove in production if desired)
    # ─────────────────────────────────────────────────────────────────────────
    @server.app.get("/get_resource_info")
    def get_resource_info():
        """Return SWML handler info for debugging."""
        return swml_handler_info

    # ─────────────────────────────────────────────────────────────────────────
    # Compatibility Routes
    # The og/twitter meta tags reference .png URLs; serve the SVG bytes at
    # those paths (matching the previous deployment's behavior).
    # ─────────────────────────────────────────────────────────────────────────
    og_image_path = web_dir / "og-image.svg"
    favicon_path = web_dir / "favicon.svg"
    og_headers = {"Cache-Control": "public, max-age=86400"}

    @server.app.get("/favicon.ico")
    def serve_favicon_ico():
        """Serve the SVG favicon for .ico requests."""
        if favicon_path.exists():
            return FileResponse(str(favicon_path), media_type="image/svg+xml")
        return JSONResponse(status_code=404, content={"error": "favicon not found"})

    @server.app.get("/og-image.png")
    def serve_og_image():
        if og_image_path.exists():
            return FileResponse(str(og_image_path), media_type="image/svg+xml", headers=og_headers)
        return JSONResponse(status_code=404, content={"error": "og-image not found"})

    @server.app.get("/og-logo.png")
    def serve_og_logo():
        if og_image_path.exists():
            return FileResponse(str(og_image_path), media_type="image/svg+xml", headers=og_headers)
        return JSONResponse(status_code=404, content={"error": "og-logo not found"})

    # ─────────────────────────────────────────────────────────────────────────
    # Startup Event
    # Register SWML handler when the application starts
    # ─────────────────────────────────────────────────────────────────────────
    @server.app.on_event("startup")
    async def on_startup():
        """Register SWML handler on application startup."""
        setup_swml_handler()

    return server


# ═══════════════════════════════════════════════════════════════════════════════
# Module-Level Exports
# ═══════════════════════════════════════════════════════════════════════════════
# These are required for gunicorn to find the application.

# Create server instance
server = create_server()

# Expose the FastAPI app for gunicorn
# Usage in Procfile: gunicorn app:app --bind 0.0.0.0:$PORT ...
app = server.app


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════
# This runs when executing the script directly (not through gunicorn).

if __name__ == "__main__":
    server.run()

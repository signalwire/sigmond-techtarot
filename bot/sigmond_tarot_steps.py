#!/usr/bin/env python3
"""
Sigmond - The SignalWire Tarot Reader
A mystical AI agent that performs tarot card readings using voice
"""

import json
import random
import secrets
import os
import argparse
from pathlib import Path
from signalwire_agents import AgentBase
from signalwire_agents.core.function_result import SwaigFunctionResult

# Use cryptographically secure random for better randomness
secure_random = secrets.SystemRandom()

class SigmondTarotReader(AgentBase):
    """Sigmond - Your mystical tarot reading assistant"""
    
    def __init__(self):
        super().__init__(
            name="Sigmond",
            route="/tarot"
        )

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
            print("Warning: signalwire_ai_knowledge_prompt.md not found!")
        
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
        
        # Define the draw_cards function
        @self.tool(
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
        def draw_cards(args, raw_data):
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
        
        # Set conversation parameters
        self.set_params({
            "video_talking_file": "https://tatooine.cantina.cloud/devuser/tarot/sigmond_tarot_talking.mp4",
            "video_idle_file": "https://tatooine.cantina.cloud/devuser/tarot/sigmond_tarot_idle.mp4",
            "vad_config": "75",
            "end_of_speech_timeout": 300,
            "max_response_tokens": 500,
            "enable_vision": True,
            #"audible_latency": True
            "background_file": "https://tatooine.cantina.cloud/devuser/tarot/bgmusic.mp3"
        })

        self.set_post_prompt("Summarize the conversation, including all the details about the tarot reading.") 
        self.set_post_prompt_url("https://NiheyBNy7sDgpyon:zmj2tuhsTyOwis6S@botworks-prod.signalwire.me/postprompt/1")
        
        # Add context about the reading
        self.set_global_data({
            "assistant_name": "Sigmond",
            "specialty": "Tarot card reading",
            "reading_style": "Three-card spread (Past, Present, Future)",
            "deck_type": "Tech-themed Tarot"
        })
    
    def _load_tarot_deck(self):
        """Load the tarot deck from JSON file"""
        # Try to find the tarot_deck.json file
        possible_paths = [
            Path(__file__).parent.parent / "web" / "tarot_deck.json",
            Path(__file__).parent / "tarot_deck.json",
            Path("/usr/local/home/devuser/src/tarot/web/tarot_deck.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
        
        # If no file found, return empty deck (should not happen in production)
        print("Warning: tarot_deck.json not found!")
        return {"major_arcana": [], "minor_arcana": {}}
    
    def _prepare_card(self, card_data):
        """Prepare a single card with orientation"""
        card = card_data["card"]
        
        # Randomly determine if card is reversed (50% chance) using secure randomness
        is_reversed = secure_random.choice([True, False])
        
        # Build the card information
        card_info = {
            "name": card["name"],
            "image": card.get("image", ""),
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


def main():
    """Run Sigmond the Tarot Reader"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Sigmond - The SignalWire Tarot Reader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python3 sigmond_tarot.py                  # Run on default port 3000
  python3 sigmond_tarot.py --port 8080      # Run on port 8080
  python3 sigmond_tarot.py -p 5000          # Run on port 5000
        """
    )
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=3000,
        help='Port to run the agent on (default: 3000)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔮 Sigmond - The SignalWire Tarot Reader")
    print("=" * 60)
    print()
    print("Sigmond is a mystical tarot reader who provides insights")
    print("into your past, present, and future using tech-themed cards.")
    print()
    print("Example things you can say:")
    print("  • 'Hello Sigmond, can you read my tarot?'")
    print("  • 'Draw my cards please'")
    print("  • 'Tell me about my future'")
    print("  • 'I'd like a tarot reading'")
    print()
    
    # Create and run Sigmond
    sigmond = SigmondTarotReader()
    
    # Get auth credentials for display
    username, password = sigmond.get_basic_auth_credentials()
    
    print(f"Sigmond is available at: http://localhost:{args.port}/tarot")
    print(f"Basic Auth: {username}:{password}")
    print()
    print(f"Starting Sigmond on port {args.port}... Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        sigmond.run(port=args.port)
    except KeyboardInterrupt:
        print("\n🔮 The spirits have departed... Until next time!")


if __name__ == "__main__":
    main()

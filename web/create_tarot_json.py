#!/usr/bin/env python3
import json
import os
import re

def parse_descriptions(desc_file):
    """Parse the desc file and extract card information."""
    cards = []
    current_card = None
    
    with open(desc_file, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # Check for arcana headers
        if line == "Major Arcana":
            i += 1
            continue
        elif line == "Minor Arcana":
            i += 1
            continue
        
        # Check for suit headers
        if line.startswith("Suit of "):
            i += 1
            continue
        
        # Check for card names
        if ("(" in line and ")" in line) or \
           line.startswith("Ace of ") or \
           line.startswith("Two of ") or \
           line.startswith("Three of ") or \
           line.startswith("Four of ") or \
           line.startswith("Five of ") or \
           line.startswith("Six of ") or \
           line.startswith("Seven of ") or \
           line.startswith("Eight of ") or \
           line.startswith("Nine of ") or \
           line.startswith("Ten of ") or \
           line.startswith("Page of ") or \
           line.startswith("Knight of ") or \
           line.startswith("Queen of ") or \
           line.startswith("King of "):
            
            if current_card:
                cards.append(current_card)
            
            current_card = {
                'name': line,
                'upright': '',
                'reversed': '',
                'yes_or_no': ''
            }
            i += 1
            continue
        
        # Parse descriptions
        if current_card:
            if line.startswith("Upright:"):
                current_card['upright'] = line[8:].strip()
            elif line.startswith("Reversed:"):
                current_card['reversed'] = line[9:].strip()
            elif line.startswith("Yes or No:"):
                current_card['yes_or_no'] = line[10:].strip()
        
        i += 1
    
    # Don't forget the last card
    if current_card:
        cards.append(current_card)
    
    return cards

def map_card_to_image(card_name, image_files):
    """Map a card name to its corresponding image file."""
    # Clean up card name for matching
    name_lower = card_name.lower()
    
    # Map special major arcana names
    major_arcana_map = {
        "the n00b": "the_noob",
        "the noob": "the_noob",
        "caffeine overflow": "caffine_overflow",  # Note the typo in the file
        "the infinite loop": "the_infinite_loop",
        "the compiler oracle": "the_compiler_oracle",
        "lord of legacy code": "lord_of_legacy_code",
        "the duck debugger": "the_duck_debugger",
        "merge conflict": "merge_conflict",
        "the market conqueror": "the_market_conqueror",
        "the lone wolf programmer": "the_lone_wolf",
        "the spinning wheel of death": "spinning_wheel_of_death",
        "order of operations": "order_of_operations",
        "the debugger": "the_debugger",
        "thread deadlock": "thread_deadlock",
        "segmentation fault": "segmentation_fault",
        "the negotiator": "the_negotiator",
        "feature creep": "feature_creep",
        "the tower of tech debt": "the_tower_of_tech_debt",
        "the rock star coder": "the_rock_star_coder",
        "mysterious bug": "mysterious_bug",
        "the enlightened algorithm": "the_enlightened_algorithm",
        "code review": "code_review",
        "the global recruiter": "the_global_recruiter"
    }
    
    # First check if it's a major arcana
    for key, value in major_arcana_map.items():
        if key in name_lower:
            for dir_name, files in image_files.items():
                if dir_name == "Major":
                    for file in files:
                        if value in file.lower():
                            return f"card_images/{dir_name}/{file}"
    
    # Handle minor arcana
    # Extract the rank and suit
    rank_map = {
        "ace": "ace",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "page": "page",
        "knight": "knight",
        "queen": "queen",
        "king": "king"
    }
    
    suit_map = {
        "linux": "Linux",
        "docker": "Docker",
        "cloud developers": "CloudDevelopers",
        "freeswitch developers": "FreeSWITCHDevs"
    }
    
    # Try to extract rank and suit
    for rank_name, rank_file in rank_map.items():
        if rank_name + " of " in name_lower:
            # Extract suit
            suit_part = name_lower.split(rank_name + " of ")[1]
            for suit_name, suit_dir in suit_map.items():
                if suit_name in suit_part:
                    # Look for the file
                    for dir_name, files in image_files.items():
                        if dir_name == suit_dir:
                            for file in files:
                                if rank_file + "_" in file:
                                    return f"card_images/{dir_name}/{file}"
    
    return None

def determine_arcana_and_suit(card_name):
    """Determine if a card is major or minor arcana and its suit."""
    name_lower = card_name.lower()
    
    # Check for minor arcana patterns
    minor_patterns = ["ace of", "two of", "three of", "four of", "five of", 
                      "six of", "seven of", "eight of", "nine of", "ten of",
                      "page of", "knight of", "queen of", "king of"]
    
    for pattern in minor_patterns:
        if pattern in name_lower:
            # It's minor arcana, determine suit
            if "linux" in name_lower:
                return "minor", "Linux"
            elif "docker" in name_lower:
                return "minor", "Docker"
            elif "cloud developer" in name_lower:
                return "minor", "Cloud Developers"
            elif "freeswitch developer" in name_lower:
                return "minor", "FreeSWITCH Developers"
    
    # If not minor, it's major
    return "major", None

def main():
    # Read image files
    image_dirs = ["Major", "Linux", "Docker", "CloudDevelopers", "FreeSWITCHDevs"]
    image_files = {}
    
    for dir_name in image_dirs:
        dir_path = f"card_images/{dir_name}"
        if os.path.exists(dir_path):
            image_files[dir_name] = os.listdir(dir_path)
    
    # Parse descriptions
    cards = parse_descriptions("desc")
    
    # Create the final JSON structure
    tarot_deck = {
        "major_arcana": [],
        "minor_arcana": {
            "Linux": [],
            "Docker": [],
            "Cloud Developers": [],
            "FreeSWITCH Developers": []
        }
    }
    
    # Process each card
    for card in cards:
        card_data = {
            "name": card['name'],
            "description": {
                "upright": card['upright'],
                "reversed": card['reversed'],
                "yes_or_no": card['yes_or_no']
            },
            "image": map_card_to_image(card['name'], image_files)
        }
        
        arcana, suit = determine_arcana_and_suit(card['name'])
        
        if arcana == "major":
            tarot_deck["major_arcana"].append(card_data)
        else:
            if suit:
                tarot_deck["minor_arcana"][suit].append(card_data)
    
    # Write to JSON file
    with open("tarot_deck.json", "w") as f:
        json.dump(tarot_deck, f, indent=2)
    
    print(f"Created tarot_deck.json with {len(cards)} cards")
    print(f"Major Arcana: {len(tarot_deck['major_arcana'])} cards")
    for suit, cards in tarot_deck["minor_arcana"].items():
        print(f"{suit}: {len(cards)} cards")

if __name__ == "__main__":
    main()
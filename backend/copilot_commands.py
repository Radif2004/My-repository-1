# copilot_commands.py
import random

COPILOT_COMMANDS = [
    "Summarize this PDF document",
    "Create a note about my meeting",
    "Set a reminder for tomorrow at 9 AM",
    "Show me all my summaries",
    "What can you help me with?"
]

def get_random_command():
    """Pick a random Copilot command from the supported list."""
    return {"command": random.choice(COPILOT_COMMANDS)}

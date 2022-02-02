import os

from disnake import ApplicationCommandInteraction
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", None) is not None
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "$")
TEST_GUILDS = (
    [int(id_) for id_ in os.getenv("TEST_GUILDS").split(",")]
    if os.getenv("TEST_GUILDS", None)
    else None
)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set")

TOKEN = os.getenv("TOKEN", "")
if not TOKEN:
    raise ValueError("TOKEN is not set")

GIT_SHA = os.getenv("GIT_SHA", "unknown")

LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "DEBUG" if DEBUG else "INFO")

# Typing aliases
ACI = ApplicationCommandInteraction

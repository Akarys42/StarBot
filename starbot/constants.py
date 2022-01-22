import os

from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "") != ""
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "$")

TOKEN = os.getenv("TOKEN", "")
if not TOKEN:
    raise ValueError("TOKEN not set")

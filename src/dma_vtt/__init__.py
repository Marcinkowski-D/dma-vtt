"""
DMA VTT - A Virtual Tabletop for Dungeon Masters and Players.

This package initializes environment variables using python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / '.env'
load_dotenv(dotenv_path)
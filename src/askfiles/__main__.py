"""Entry point for `python -m askfiles`."""
import sys

from .cli import main

# The Windows console may not be able to print every character of an answer.
sys.stdout.reconfigure(errors="replace")
sys.exit(main())

#!/usr/bin/env python3
"""
Utility functions shared across the Essen Route Planning pipeline.
"""

import os
import sys
from typing import Optional


def is_interactive_terminal() -> bool:
    """Check if we're running in an interactive terminal."""
    return os.isatty(sys.stdin.fileno()) and os.isatty(sys.stdout.fileno())


def safe_input(prompt: str, default: Optional[str] = None) -> str:
    """Safe input that works in both interactive and non-interactive environments."""
    if not is_interactive_terminal():
        if default is not None:
            print(f"{prompt}[Non-interactive: using default '{default}']")
            return default
        else:
            print(f"❌ Error: {prompt}")
            print("   Running in non-interactive environment but no default provided.")
            print("   Please run with appropriate command-line flags or in interactive terminal.")
            sys.exit(1)
    
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        if default is not None:
            print(f"\nNo input provided, using default '{default}'.")
            return default
        else:
            print(f"❌ Error: No input provided for: {prompt}")
            print("   Please provide input or run with appropriate command-line flags.")
            sys.exit(1)
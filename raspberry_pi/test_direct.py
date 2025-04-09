#!/usr/bin/env python3
"""
Test script for direct database access.
"""

import sys
import json
from database_direct import get_alarm_by_id

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python test_direct.py <alarm_id>")
        sys.exit(1)
    
    alarm_id = int(sys.argv[1])
    alarm = get_alarm_by_id(alarm_id)
    
    if alarm:
        print(f"Found alarm with ID {alarm.id}")
        print(f"  Time: {alarm.time}")
        print(f"  Enabled: {alarm.enabled}")
        print(f"  Repeating: {alarm.repeating}")
        print(f"  Days: {alarm.days}")
        print(f"  Is TTS: {alarm.is_tts}")
        print(f"  Message: {alarm.message}")
        print(f"  Sound path: {alarm.sound_path}")
        print(f"  Label: '{alarm.label}'")
        
        # Also print as dict
        print("\nAs dictionary:")
        print(json.dumps(alarm.to_dict(), indent=2, default=str))
    else:
        print(f"No alarm found with ID {alarm_id}")

if __name__ == "__main__":
    main()
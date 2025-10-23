#!/usr/bin/env python3
"""
Startup script for the LAN Communication Client
"""

import sys
import os

# Add client directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'client'))

def main():
    """Start the client"""
    print("🌐 Starting LAN Communication Client...")
    print("=" * 50)
    
    try:
        from main_client import main
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting client: {e}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Startup script for the LAN Communication Server
"""

import sys
import os

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

def main():
    """Start the server"""
    print("🌐 Starting LAN Communication Server...")
    print("=" * 50)
    
    try:
        from main_server import main
        main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()

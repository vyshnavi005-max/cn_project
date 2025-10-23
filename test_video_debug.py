#!/usr/bin/env python3
"""
Test script to debug video conferencing issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.main_client import LANCommunicationClient

def test_video_connection():
    """Test video connection with debug output"""
    print("Testing Video Connection...")
    print("=" * 50)
    
    # Create client
    client = LANCommunicationClient('localhost', 6000)
    
    # Connect
    if client.connect_to_server('testuser'):
        print("Connected to server")
        
        # Start camera
        if client.video_client and client.video_client.start_camera():
            print("Camera started")
            
            # Wait a bit to see if frames are being sent
            import time
            print("Waiting 10 seconds to test video flow...")
            time.sleep(10)
            
            # Check if frames were sent
            if hasattr(client.video_client, 'frame_count'):
                print(f"Frames sent: {client.video_client.frame_count}")
            else:
                print("No frames sent")
                
            # Stop camera
            client.video_client.stop_camera()
        else:
            print("Camera failed to start")
    else:
        print("Failed to connect to server")
    
    # Disconnect
    client.disconnect()

if __name__ == "__main__":
    test_video_connection()

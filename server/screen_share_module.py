#!/usr/bin/env python3
"""
Screen Share Module - Handles screen/slide sharing using TCP
"""

import threading
import time
import base64
from datetime import datetime

class ScreenShareModule:
    def __init__(self, server):
        self.server = server
        self.running = False
        self.screen_thread = None
        self.current_presenter = None
        self.presentation_active = False
        self.frame_buffer = None
        self.frame_lock = threading.Lock()
        
    def start(self):
        """Start the screen share module"""
        self.running = True
        self.screen_thread = threading.Thread(target=self.screen_loop, daemon=True)
        self.screen_thread.start()
        print("🖼️ Screen share module started")
    
    def stop(self):
        """Stop the screen share module"""
        self.running = False
        if self.screen_thread:
            self.screen_thread.join()
        print("🖼️ Screen share module stopped")
    
    def screen_loop(self):
        """Main screen share processing loop"""
        while self.running:
            time.sleep(0.1)  # 10 FPS for screen sharing
    
    def start_presentation(self, username, message_data):
        """Start screen sharing for a user"""
        if not self.running or username not in self.server.clients:
            return False
        
        # Check if someone else is already presenting
        if self.presentation_active and self.current_presenter != username:
            # Stop current presentation
            self.stop_presentation(self.current_presenter)
        
        # Start new presentation
        self.current_presenter = username
        self.presentation_active = True
        
        # Notify all clients
        notification = {
            'type': 'presentation_started',
            'presenter': username,
            'timestamp': datetime.now().isoformat()
        }
        self.server.broadcast_to_all(notification)
        
        print(f"🖼️ {username} started screen sharing")
        return True
    
    def stop_presentation(self, username):
        """Stop screen sharing for a user"""
        if self.current_presenter == username:
            self.current_presenter = None
            self.presentation_active = False
            
            # Clear frame buffer
            with self.frame_lock:
                self.frame_buffer = None
            
            # Notify all clients
            notification = {
                'type': 'presentation_stopped',
                'presenter': username,
                'timestamp': datetime.now().isoformat()
            }
            self.server.broadcast_to_all(notification)
            
            print(f"🖼️ {username} stopped screen sharing")
    
    def handle_frame(self, username, message_data, client_socket):
        """Handle incoming screen frame from presenter"""
        if not self.running or not self.presentation_active:
            return
        
        if self.current_presenter != username:
            return
        
        frame_data = message_data.get('frame_data', '')
        frame_format = message_data.get('format', 'jpeg')
        timestamp = message_data.get('timestamp', time.time())
        
        if not frame_data:
            return
        
        # Store latest frame
        with self.frame_lock:
            self.frame_buffer = {
                'frame_data': frame_data,
                'format': frame_format,
                'timestamp': timestamp,
                'presenter': username
            }
        
        # Broadcast frame to all other clients
        self.broadcast_frame(username, frame_data, frame_format, timestamp)
    
    def broadcast_frame(self, presenter_username, frame_data, frame_format, timestamp):
        """Broadcast screen frame to all other clients"""
        if not self.server.clients:
            return
        
        # Create frame packet
        frame_packet = {
            'type': 'screen_frame',
            'frame_data': frame_data,
            'format': frame_format,
            'timestamp': timestamp,
            'presenter': presenter_username
        }
        
        # Send to all other clients
        for username in self.server.clients:
            if username != presenter_username:
                self.server.send_to_client(username, frame_packet)
    
    def get_current_frame(self):
        """Get current screen frame (for debugging)"""
        with self.frame_lock:
            return self.frame_buffer.copy() if self.frame_buffer else None
    
    def is_presentation_active(self):
        """Check if presentation is currently active"""
        return self.presentation_active
    
    def get_current_presenter(self):
        """Get current presenter username"""
        return self.current_presenter
    
    def request_presentation_control(self, username):
        """Request to take over presentation"""
        if not self.running or username not in self.server.clients:
            return False
        
        if self.presentation_active and self.current_presenter != username:
            # Ask current presenter to stop
            request = {
                'type': 'presentation_handover_request',
                'requester': username,
                'timestamp': datetime.now().isoformat()
            }
            self.server.send_to_client(self.current_presenter, request)
            return True
        
        return False
    
    def compress_frame(self, frame_data, quality=70):
        """Compress screen frame (placeholder for actual compression)"""
        try:
            # For now, just return the data as-is
            # In a real implementation, you would compress the image here
            return frame_data
        except Exception as e:
            print(f"❌ Error compressing frame: {e}")
            return None
    
    def decompress_frame(self, compressed_data, format_type='jpeg'):
        """Decompress screen frame (placeholder for actual decompression)"""
        try:
            # For now, just return the data as-is
            # In a real implementation, you would decompress the image here
            return compressed_data
        except Exception as e:
            print(f"❌ Error decompressing frame: {e}")
            return None

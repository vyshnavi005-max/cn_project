#!/usr/bin/env python3
"""
Video Module - Handles video streaming using UDP for low latency
"""

import socket
import threading
import time
import struct
import cv2
import numpy as np
from datetime import datetime

class VideoModule:
    def __init__(self, server):
        self.server = server
        self.running = False
        self.video_thread = None
        self.frame_buffer = {}  # {username: latest_frame}
        self.frame_lock = threading.Lock()
        
    def start(self):
        """Start the video module"""
        self.running = True
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()
        print("Video module started")
    
    def stop(self):
        """Stop the video module"""
        self.running = False
        if self.video_thread:
            self.video_thread.join()
        print("Video module stopped")
    
    def video_loop(self):
        """Main video processing loop"""
        while self.running:
            try:
                # Set socket timeout to prevent blocking
                self.server.video_udp_socket.settimeout(1.0)
                # Receive video data from clients
                data, addr = self.server.video_udp_socket.recvfrom(65536)
                
                # Parse video packet
                if len(data) > 8:
                    # Extract username length and username
                    username_len = struct.unpack('!I', data[:4])[0]
                    username = data[4:4+username_len].decode('utf-8')
                    
                    # Extract frame data
                    frame_data = data[4+username_len:]
                    
                    # Store frame for this user
                    with self.frame_lock:
                        self.frame_buffer[username] = {
                            'frame_data': frame_data,
                            'timestamp': time.time(),
                            'address': addr
                        }
                    
                    # Broadcast to all other clients
                    self.broadcast_frame(username, frame_data, addr)
                    
            except socket.timeout:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"Video module error: {e}")
                time.sleep(0.01)
    
    def broadcast_frame(self, sender_username, frame_data, sender_addr):
        """Broadcast video frame to all other clients"""
        if not self.server.clients:
            return
        
        # Create broadcast packet
        username_len = len(sender_username.encode('utf-8'))
        packet = struct.pack('!I', username_len) + sender_username.encode('utf-8') + frame_data
        
        # Send to all other clients
        for username, client_data in self.server.clients.items():
            if username != sender_username and client_data.get('video_udp_addr'):
                try:
                    self.server.video_udp_socket.sendto(packet, client_data['video_udp_addr'])
                except Exception as e:
                    print(f"Error broadcasting to {username}: {e}")
    
    def set_client_udp_address(self, username, udp_addr):
        """Set UDP address for a client"""
        if username in self.server.clients:
            self.server.clients[username]['video_udp_addr'] = udp_addr
            print(f"Set UDP address for {username}: {udp_addr}")
    
    def get_frame_buffer(self):
        """Get current frame buffer (for debugging)"""
        with self.frame_lock:
            return self.frame_buffer.copy()
    
    def compress_frame(self, frame, quality=50):
        """Compress video frame using JPEG"""
        try:
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            
            if result:
                return encoded_img.tobytes()
            return None
        except Exception as e:
            print(f"Error compressing frame: {e}")
            return None
    
    def decompress_frame(self, frame_data):
        """Decompress video frame from JPEG"""
        try:
            # Decode JPEG data
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"Error decompressing frame: {e}")
            return None
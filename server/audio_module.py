#!/usr/bin/env python3
"""
Audio Module - Handles audio streaming and mixing using UDP
"""

import socket
import threading
import time
import struct
import numpy as np
from datetime import datetime

class AudioModule:
    def __init__(self, server):
        self.server = server
        self.running = False
        self.audio_thread = None
        self.audio_buffer = {}  # {username: audio_data}
        self.audio_lock = threading.Lock()
        
        # Audio parameters
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024
        
    def start(self):
        """Start the audio module"""
        self.running = True
        self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.audio_thread.start()
        print("Audio module started")
    
    def stop(self):
        """Stop the audio module"""
        self.running = False
        if self.audio_thread:
            self.audio_thread.join()
        print("Audio module stopped")
    
    def audio_loop(self):
        """Main audio processing loop"""
        while self.running:
            try:
                # Set socket timeout to prevent blocking
                self.server.audio_udp_socket.settimeout(1.0)
                # Receive audio data from clients
                data, addr = self.server.audio_udp_socket.recvfrom(4096)
                
                # Parse audio packet
                if len(data) > 8:
                    # Extract username length and username
                    username_len = struct.unpack('!I', data[:4])[0]
                    username = data[4:4+username_len].decode('utf-8')
                    
                    # Extract audio data
                    audio_data = data[4+username_len:]
                    
                    # Store audio for this user
                    with self.audio_lock:
                        self.audio_buffer[username] = {
                            'audio_data': audio_data,
                            'timestamp': time.time(),
                            'address': addr
                        }
                    
                    # Mix and broadcast to all other clients
                    self.mix_and_broadcast_audio(username, audio_data, addr)
                    
            except socket.timeout:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"Audio module error: {e}")
                time.sleep(0.01)
    
    def mix_and_broadcast_audio(self, sender_username, sender_audio_data, sender_addr):
        """Mix audio from all users and broadcast to all clients"""
        if not self.server.clients:
            return
        
        # Get all audio data
        with self.audio_lock:
            all_audio = {}
            for username, audio_info in self.audio_buffer.items():
                if username != sender_username:  # Don't include sender in mix
                    all_audio[username] = audio_info['audio_data']
        
        if not all_audio:
            return
        
        # Mix audio data
        try:
            mixed_audio = self.mix_audio_data(list(all_audio.values()))
            usernames = list(all_audio.keys())
            
            # Create broadcast packet
            packet = self.create_audio_packet(usernames, mixed_audio)
            
            # Send to all clients
            for username, client_data in self.server.clients.items():
                if client_data.get('audio_udp_addr'):
                    try:
                        self.server.audio_udp_socket.sendto(packet, client_data['audio_udp_addr'])
                    except Exception as e:
                        print(f"Error broadcasting audio to {username}: {e}")
                        
        except Exception as e:
            print(f"Error mixing audio: {e}")
    
    def mix_audio_data(self, audio_data_list):
        """Mix multiple audio data streams"""
        if not audio_data_list:
            return b''
        
        try:
            # Convert bytes to numpy arrays
            audio_arrays = []
            for audio_data in audio_data_list:
                if len(audio_data) > 0:
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    audio_arrays.append(audio_array)
            
            if not audio_arrays:
                return b''
            
            # Mix by averaging
            mixed_array = np.mean(audio_arrays, axis=0).astype(np.int16)
            return mixed_array.tobytes()
            
        except Exception as e:
            print(f"Error mixing audio arrays: {e}")
            return b''
    
    def create_audio_packet(self, usernames, audio_data):
        """Create audio packet with usernames and audio data"""
        packet = struct.pack('!I', len(usernames))  # Number of users
        
        # Add usernames separated by null bytes
        for username in usernames:
            packet += username.encode('utf-8') + b'\x00'
        
        # Add audio data
        packet += audio_data
        
        return packet
    
    def set_client_udp_address(self, username, udp_addr):
        """Set UDP address for a client"""
        if username in self.server.clients:
            self.server.clients[username]['audio_udp_addr'] = udp_addr
            print(f"Set audio UDP address for {username}: {udp_addr}")
    
    def get_audio_buffer(self):
        """Get current audio buffer (for debugging)"""
        with self.audio_lock:
            return self.audio_buffer.copy()
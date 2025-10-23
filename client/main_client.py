#!/usr/bin/env python3
"""
LAN Communication Client - Main Client Controller
Connects to server and manages all communication modules
"""

import socket
import threading
import json
import sys
import os
import time
from datetime import datetime

# Add client directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from video_client import VideoClient
from audio_client import AudioClient
from chat_client import ChatClient
from file_client import FileClient
from screen_share_client import ScreenShareClient
from ui.main_window import MainWindow

class LANCommunicationClient:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.connected = False
        self.running = False
        
        # Sockets
        self.tcp_socket = None
        self.video_udp_socket = None
        self.audio_udp_socket = None
        
        # Modules
        self.video_client = None
        self.audio_client = None
        self.chat_client = None
        self.file_client = None
        self.screen_share_client = None
        self.main_window = None
        
        # Threads
        self.receive_thread = None
        self.video_thread = None
        self.audio_thread = None
        
    def connect_to_server(self, username):
        """Connect to the server"""
        try:
            # Create TCP socket for reliable communication
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.server_host, self.server_port))
            
            # Create UDP sockets for video and audio
            self.video_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow socket reuse to prevent binding errors
            self.video_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.audio_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind UDP sockets to local ports (let OS choose available ports)
            self.video_udp_socket.bind(('', 0))  # Bind to any available port
            self.audio_udp_socket.bind(('', 0))  # Bind to any available port
            
            # Get the actual bound ports
            self.video_local_port = self.video_udp_socket.getsockname()[1]
            self.audio_local_port = self.audio_udp_socket.getsockname()[1]
            
            print(f"Video UDP bound to local port: {self.video_local_port}")
            print(f"Audio UDP bound to local port: {self.audio_local_port}")
            
            # Register with server
            self.username = username
            registration = {
                'type': 'register',
                'username': username,
                'client_time': datetime.now().isoformat(),
                'video_udp_port': self.video_local_port,
                'audio_udp_port': self.audio_local_port
            }
            self.send_tcp_message(registration)
            
            # Wait for registration confirmation
            response = self.receive_tcp_message()
            if response and response.get('type') == 'registration_success':
                self.connected = True
                self.running = True
                
                # Start receive thread
                self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
                self.receive_thread.start()
                
                # Initialize modules
                self.initialize_modules()
                
                print(f"Connected to server as {username}")
                return True
            else:
                print(f"Registration failed: {response}")
                return False
                
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def initialize_modules(self):
        """Initialize all client modules"""
        # Initialize video client
        self.video_client = VideoClient(self)
        
        # Initialize audio client
        self.audio_client = AudioClient(self)
        
        # Initialize chat client
        self.chat_client = ChatClient(self)
        
        # Initialize file client
        self.file_client = FileClient(self)
        
        # Initialize screen share client
        self.screen_share_client = ScreenShareClient(self)
        
        # Initialize main window
        self.main_window = MainWindow(self)
        
        # Start video and audio threads
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
        
        self.video_thread.start()
        self.audio_thread.start()
    
    def receive_loop(self):
        """Main receive loop for TCP messages"""
        buffer = ""
        while self.running and self.connected:
            try:
                data = self.tcp_socket.recv(4096)
                if data:
                    buffer += data.decode('utf-8')
                    
                    # Process complete messages (separated by newlines)
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                message = json.loads(line.strip())
                                self.handle_server_message(message)
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}")
                                print(f"Problematic data: {line[:100]}...")
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
    
    def handle_server_message(self, message):
        """Handle incoming message from server"""
        message_type = message.get('type')
        
        if message_type == 'user_list_update':
            if self.main_window:
                self.main_window.update_user_list(message.get('users', []))
            
        elif message_type == 'chat_message':
            if self.chat_client:
                self.chat_client.handle_message(message.get('data'))
            
        elif message_type == 'system_message':
            if self.chat_client:
                self.chat_client.handle_system_message(message.get('data'))
            
        elif message_type == 'file_available':
            if self.file_client:
                self.file_client.handle_file_available(message.get('file_info'))
            
        elif message_type == 'presentation_started':
            if self.screen_share_client:
                self.screen_share_client.handle_presentation_started(message)
            
        elif message_type == 'presentation_stopped':
            if self.screen_share_client:
                self.screen_share_client.handle_presentation_stopped(message)
            
        elif message_type == 'screen_frame':
            if self.screen_share_client:
                self.screen_share_client.handle_screen_frame(message)
            
        elif message_type == 'error':
            print(f"Server error: {message.get('message')}")
    
    def video_loop(self):
        """Video processing loop"""
        while self.running and self.connected:
            try:
                # Set socket timeout to prevent blocking
                self.video_udp_socket.settimeout(1.0)
                # Receive video data from server
                data, addr = self.video_udp_socket.recvfrom(65536)
                
                if len(data) > 8:
                    # Parse video packet
                    import struct
                    username_len = struct.unpack('!I', data[:4])[0]
                    username = data[4:4+username_len].decode('utf-8')
                    frame_data = data[4+username_len:]
                    
                    # Handle video frame
                    if self.video_client:
                        self.video_client.handle_received_frame(username, frame_data)
                    
            except socket.timeout:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"Video loop error: {e}")
                time.sleep(0.01)
    
    def audio_loop(self):
        """Audio processing loop"""
        while self.running and self.connected:
            try:
                # Set socket timeout to prevent blocking
                self.audio_udp_socket.settimeout(1.0)
                # Receive audio data from server
                data, addr = self.audio_udp_socket.recvfrom(4096)
                
                if len(data) > 8:
                    # Parse audio packet
                    import struct
                    user_count = struct.unpack('!I', data[:4])[0]
                    offset = 4
                    
                    # Extract usernames
                    usernames = []
                    for _ in range(user_count):
                        username_end = data.find(b'\x00', offset)
                        if username_end == -1:
                            break
                        usernames.append(data[offset:username_end].decode('utf-8'))
                        offset = username_end + 1
                    
                    # Extract audio data
                    audio_data = data[offset:]
                    
                    # Handle mixed audio
                    if self.audio_client:
                        self.audio_client.handle_mixed_audio(audio_data, usernames)
                    
            except socket.timeout:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                if self.running:
                    print(f"Audio loop error: {e}")
                time.sleep(0.01)
    
    def send_tcp_message(self, message):
        """Send TCP message to server"""
        try:
            data = json.dumps(message).encode('utf-8')
            self.tcp_socket.send(data)
        except Exception as e:
            print(f"Error sending TCP message: {e}")
    
    def receive_tcp_message(self):
        """Receive TCP message from server"""
        try:
            data = self.tcp_socket.recv(4096)
            if data:
                # Handle multiple JSON messages in one packet
                message_str = data.decode('utf-8')
                
                # Try to parse as single JSON first
                try:
                    return json.loads(message_str)
                except json.JSONDecodeError:
                    # If that fails, try to find complete JSON messages
                    messages = []
                    decoder = json.JSONDecoder()
                    idx = 0
                    
                    while idx < len(message_str):
                        try:
                            obj, end_idx = decoder.raw_decode(message_str, idx)
                            messages.append(obj)
                            idx = end_idx
                        except json.JSONDecodeError:
                            break
                    
                    # Return the first valid message
                    if messages:
                        return messages[0]
                    else:
                        print(f"Could not parse JSON: {message_str[:100]}...")
                        return None
        except Exception as e:
            print(f"Error receiving TCP message: {e}")
        return None
    
    def send_video_frame(self, frame_data):
        """Send video frame to server"""
        if not self.connected or not self.username:
            return
        
        try:
            import struct
            username_bytes = self.username.encode('utf-8')
            packet = struct.pack('!I', len(username_bytes)) + username_bytes + frame_data
            self.video_udp_socket.sendto(packet, (self.server_host, self.server_port + 1))
        except Exception as e:
            print(f"Error sending video frame: {e}")
    
    def send_audio_data(self, audio_data):
        """Send audio data to server"""
        if not self.connected or not self.username:
            return
        
        try:
            import struct
            username_bytes = self.username.encode('utf-8')
            packet = struct.pack('!I', len(username_bytes)) + username_bytes + audio_data
            self.audio_udp_socket.sendto(packet, (self.server_host, self.server_port + 2))
        except Exception as e:
            print(f"Error sending audio data: {e}")
    
    def send_chat_message(self, message):
        """Send chat message to server"""
        if not self.connected:
            return
        
        chat_message = {
            'type': 'chat',
            'message': message
        }
        self.send_tcp_message(chat_message)
    
    def send_file_upload(self, filename, file_size, file_hash):
        """Send file upload request to server"""
        if not self.connected:
            return
        
        upload_request = {
            'type': 'file_upload',
            'filename': filename,
            'file_size': file_size,
            'file_hash': file_hash
        }
        self.send_tcp_message(upload_request)
    
    def send_file_download(self, file_id):
        """Send file download request to server"""
        if not self.connected:
            return
        
        download_request = {
            'type': 'file_download',
            'file_id': file_id
        }
        self.send_tcp_message(download_request)
    
    def start_screen_sharing(self):
        """Start screen sharing"""
        if not self.connected:
            return
        
        share_request = {
            'type': 'screen_share_start',
            'timestamp': datetime.now().isoformat()
        }
        self.send_tcp_message(share_request)
    
    def stop_screen_sharing(self):
        """Stop screen sharing"""
        if not self.connected:
            return
        
        stop_request = {
            'type': 'screen_share_stop',
            'timestamp': datetime.now().isoformat()
        }
        self.send_tcp_message(stop_request)
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.connected = False
        
        # Close sockets
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.video_udp_socket:
            self.video_udp_socket.close()
        if self.audio_udp_socket:
            self.audio_udp_socket.close()
        
        print("Disconnected from server")
    
    def run(self):
        """Run the client application"""
        try:
            # Get username
            username = input("Enter your username: ").strip()
            if not username:
                print("Username cannot be empty")
                return
            
            # Connect to server
            if not self.connect_to_server(username):
                return
            
            # Start GUI
            self.main_window.run()
            
        except KeyboardInterrupt:
            print("\nShutting down client...")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            self.disconnect()

def main():
    """Main entry point"""
    print("LAN Communication Client")
    print("=" * 50)
    
    # Get server connection info
    server_host = input("Enter server IP (default: localhost): ").strip() or 'localhost'
    server_port = input("Enter server port (default: 5000): ").strip() or '5000'
    
    try:
        server_port = int(server_port)
    except ValueError:
        print("Invalid port number, using default 5000")
        server_port = 5000
    
    # Create and run client
    client = LANCommunicationClient(server_host, server_port)
    client.run()

if __name__ == "__main__":
    main()
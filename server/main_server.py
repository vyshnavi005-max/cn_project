#!/usr/bin/env python3
"""
LAN Communication Server - Main Server Controller
Handles client connections and coordinates all communication modules
"""

import socket
import threading
import json
import time
from datetime import datetime
import sys
import os

# Add server directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from video_module import VideoModule
from audio_module import AudioModule
from chat_module import ChatModule
from file_module import FileModule
from screen_share_module import ScreenShareModule
from utils.helpers import setup_logging, log_event

class LANCommunicationServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.clients = {}  # {username: {socket, address, status, udp_addr}}
        self.current_presenter = None
        self.running = False
        
        # Initialize modules
        self.video_module = VideoModule(self)
        self.audio_module = AudioModule(self)
        self.chat_module = ChatModule(self)
        self.file_module = FileModule(self)
        self.screen_share_module = ScreenShareModule(self)
        
        # Setup logging
        setup_logging()
        
        # Create sockets
        self.tcp_socket = None
        self.video_udp_socket = None
        self.audio_udp_socket = None
        
    def start_server(self):
        """Start the main server and all modules"""
        try:
            # Create TCP socket for reliable communication
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.host, self.port))
            self.tcp_socket.listen(10)
            
            # Create UDP sockets for video and audio
            self.video_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_udp_socket.bind((self.host, self.port + 1))
            
            self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_udp_socket.bind((self.host, self.port + 2))
            
            self.running = True
            
            print(f"Server started on {self.host}:{self.port}")
            print(f"Video UDP port: {self.port + 1}")
            print(f"Audio UDP port: {self.port + 2}")
            print("=" * 50)
            
            # Start module threads
            self.video_module.start()
            self.audio_module.start()
            self.chat_module.start()
            self.file_module.start()
            self.screen_share_module.start()
            
            # Start accepting client connections
            self.accept_connections()
            
        except Exception as e:
            print(f"Error starting server: {e}")
            self.stop_server()
    
    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, client_address = self.tcp_socket.accept()
                print(f"New connection from {client_address}")
                
                # Start thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                break
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client communication"""
        username = None
        try:
            while self.running:
                # Receive message from client
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    message_type = message.get('type')
                    
                    if message_type == 'register':
                        username = message.get('username')
                        video_udp_port = message.get('video_udp_port')
                        audio_udp_port = message.get('audio_udp_port')
                        if username and username not in self.clients:
                            self.register_client(username, client_socket, client_address, video_udp_port, audio_udp_port)
                        else:
                            self.send_error(client_socket, "Username already taken")
                            
                    elif message_type == 'chat':
                        self.chat_module.handle_message(username, message)
                        
                    elif message_type == 'file_upload':
                        self.file_module.handle_upload(username, message, client_socket)
                        
                    elif message_type == 'file_download':
                        self.file_module.handle_download(username, message, client_socket)
                        
                    elif message_type == 'screen_share_start':
                        self.screen_share_module.start_presentation(username, message)
                        
                    elif message_type == 'screen_share_stop':
                        self.screen_share_module.stop_presentation(username)
                        
                    elif message_type == 'screen_frame':
                        self.screen_share_module.handle_frame(username, message, client_socket)
                        
                except json.JSONDecodeError:
                    print(f"Invalid JSON from {client_address}")
                except Exception as e:
                    print(f"Error handling message: {e}")
                    
        except Exception as e:
            print(f"Error in client handler: {e}")
        finally:
            if username:
                self.unregister_client(username)
            client_socket.close()
    
    def register_client(self, username, client_socket, client_address, video_udp_port=None, audio_udp_port=None):
        """Register a new client"""
        # Calculate UDP addresses for this client
        video_udp_addr = None
        audio_udp_addr = None
        
        if video_udp_port:
            video_udp_addr = (client_address[0], video_udp_port)
        if audio_udp_port:
            audio_udp_addr = (client_address[0], audio_udp_port)
        
        self.clients[username] = {
            'socket': client_socket,
            'address': client_address,
            'status': 'online',
            'video_udp_addr': video_udp_addr,
            'audio_udp_addr': audio_udp_addr,
            'joined_at': datetime.now()
        }
        
        # Set UDP addresses in video and audio modules
        if video_udp_addr:
            self.video_module.set_client_udp_address(username, video_udp_addr)
        if audio_udp_addr:
            self.audio_module.set_client_udp_address(username, audio_udp_addr)
        
        print(f"Set video UDP address for {username}: {video_udp_addr}")
        print(f"Set audio UDP address for {username}: {audio_udp_addr}")
        
        # Send registration confirmation
        response = {
            'type': 'registration_success',
            'username': username,
            'server_time': datetime.now().isoformat()
        }
        self.send_to_client(username, response)
        
        # Notify other clients
        self.broadcast_user_list()
        self.chat_module.broadcast_system_message(f"{username} joined the session")
        
        log_event(f"User {username} registered from {client_address}")
        print(f"{username} registered successfully")
    
    def unregister_client(self, username):
        """Unregister a client"""
        if username in self.clients:
            del self.clients[username]
            
            # If this user was presenting, stop presentation
            if self.current_presenter == username:
                self.current_presenter = None
                self.screen_share_module.stop_presentation(username)
            
            # Notify other clients
            self.broadcast_user_list()
            self.chat_module.broadcast_system_message(f"{username} left the session")
            
            log_event(f"User {username} disconnected")
            print(f"{username} disconnected")
    
    def send_to_client(self, username, message):
        """Send message to specific client"""
        if username in self.clients:
            try:
                data = json.dumps(message).encode('utf-8')
                # Add newline to separate messages
                data += b'\n'
                self.clients[username]['socket'].send(data)
            except Exception as e:
                print(f"Error sending to {username}: {e}")
    
    def broadcast_to_all(self, message, exclude_username=None):
        """Broadcast message to all connected clients"""
        for username in self.clients:
            if username != exclude_username:
                self.send_to_client(username, message)
    
    def broadcast_user_list(self):
        """Broadcast updated user list to all clients"""
        user_list = []
        for username, client_data in self.clients.items():
            user_list.append({
                'username': username,
                'status': client_data['status'],
                'joined_at': client_data['joined_at'].isoformat()
            })
        
        message = {
            'type': 'user_list_update',
            'users': user_list,
            'current_presenter': self.current_presenter
        }
        self.broadcast_to_all(message)
    
    def send_error(self, client_socket, error_message):
        """Send error message to client"""
        error = {
            'type': 'error',
            'message': error_message
        }
        try:
            data = json.dumps(error).encode('utf-8')
            client_socket.send(data)
        except Exception as e:
            print(f"Error sending error message: {e}")
    
    def stop_server(self):
        """Stop the server and cleanup"""
        self.running = False
        
        # Stop all modules
        self.video_module.stop()
        self.audio_module.stop()
        self.chat_module.stop()
        self.file_module.stop()
        self.screen_share_module.stop()
        
        # Close sockets
        if self.tcp_socket:
            self.tcp_socket.close()
        if self.video_udp_socket:
            self.video_udp_socket.close()
        if self.audio_udp_socket:
            self.audio_udp_socket.close()
        
        print("Server stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LAN Communication Server')
    parser.add_argument('host', nargs='?', default='0.0.0.0', help='Server IP address')
    parser.add_argument('port', nargs='?', type=int, default=5000, help='Server port')
    
    args = parser.parse_args()
    
    print("LAN Communication Server")
    print("=" * 50)
    
    # Create and start server
    server = LANCommunicationServer(args.host, args.port)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop_server()
    except Exception as e:
        print(f"Server error: {e}")
        server.stop_server()

if __name__ == "__main__":
    main()
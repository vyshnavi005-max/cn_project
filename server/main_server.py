#!/usr/bin/env python3
"""
LAN Communication Server - Main Server Controller
Handles client connections and coordinates all communication modules
"""

#!/usr/bin/env python3
"""
LAN Communication Server - Main Server Controller
Handles client connections and coordinates all communication modules
(Modified with TCP Message Framing)
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
# Import the new helper functions along with existing ones
from utils.helpers import setup_logging, log_event, log_error, send_framed_message, receive_framed_message

class LANCommunicationServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.clients = {}  # {username: {socket, address, status, video_udp_addr, audio_udp_addr, joined_at}}
        self.current_presenter = None # Keep track of who is screen sharing
        self.running = False

        # Use a lock for thread-safe access to the clients dictionary
        self.clients_lock = threading.Lock()

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
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((self.host, self.port))
            self.tcp_socket.listen(10) # Allow up to 10 pending connections

            # Create UDP sockets
            self.video_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.video_udp_socket.bind((self.host, self.port + 1))

            self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_udp_socket.bind((self.host, self.port + 2))

            self.running = True

            print(f"✅ Server started on {self.host}:{self.port}")
            log_event(f"Server started listening on {self.host}:{self.port}")
            print(f"📹 Video UDP port: {self.port + 1}")
            print(f"🎵 Audio UDP port: {self.port + 2}")
            print("=" * 50)

            # Start module threads
            self.video_module.start()
            self.audio_module.start()
            self.chat_module.start()
            self.file_module.start()
            self.screen_share_module.start()

            # Start accepting client connections in a separate thread
            accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            accept_thread.start()

            # Keep the main thread alive (optional, could just rely on accept_connections loop)
            while self.running:
                time.sleep(1)

        except OSError as e:
            log_error(f"Error starting server (Address likely already in use): {e}")
            print(f"❌ Error starting server: {e}. Is port {self.port} already in use?")
            self.stop_server()
        except Exception as e:
            log_error(f"Error starting server: {e}")
            print(f"❌ Error starting server: {e}")
            self.stop_server()

    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                # Set a timeout on accept to allow checking self.running periodically
                self.tcp_socket.settimeout(1.0)
                client_socket, client_address = self.tcp_socket.accept()
                self.tcp_socket.settimeout(None) # Remove timeout for the client socket itself

                log_event(f"New connection from {client_address}")
                print(f"🤝 New connection from {client_address}")

                # Start thread to handle this client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True # Daemon threads exit when the main program exits
                )
                client_thread.start()

            except socket.timeout:
                continue # Just loop again to check self.running
            except Exception as e:
                if self.running:
                    log_error(f"Error accepting connection: {e}")
                    print(f"❌ Error accepting connection: {e}")
                break # Exit loop if running is false or accept fails unexpectedly

        log_event("Stopped accepting connections.")

    def handle_client(self, client_socket, client_address):
        """Handle individual client communication using framed messages"""
        username = None
        try:
            while self.running:
                # Receive a framed message
                message = receive_framed_message(client_socket)

                # If receive_framed_message returns None, the connection is likely closed or broken
                if message is None:
                    log_event(f"Connection lost or closed for {client_address} (User: {username or 'Unregistered'})")
                    break

                message_type = message.get('type')
                # Log received message type for debugging
                # log_event(f"Received message type '{message_type}' from {username or client_address}")

                if message_type == 'register':
                    temp_username = message.get('username')
                    video_udp_port = message.get('video_udp_port')
                    audio_udp_port = message.get('audio_udp_port')

                    # Simple validation
                    is_valid_user = temp_username and isinstance(temp_username, str) and 3 <= len(temp_username) <= 20

                    with self.clients_lock: # Lock before checking/modifying clients dict
                        if is_valid_user and temp_username not in self.clients:
                            username = temp_username # Assign username only upon successful registration
                            self.register_client(username, client_socket, client_address, video_udp_port, audio_udp_port)
                        elif not is_valid_user:
                             self.send_error(client_socket, "Invalid username format (3-20 alphanumeric chars).")
                             log_warning(f"Registration failed for {client_address}: Invalid username '{temp_username}'")
                             break # Close connection for invalid registration attempt
                        else:
                            self.send_error(client_socket, f"Username '{temp_username}' already taken.")
                            log_warning(f"Registration failed for {client_address}: Username '{temp_username}' taken.")
                            break # Close connection for duplicate username attempt

                # --- Message Handling (Requires client to be registered first) ---
                elif username: # Only process other messages if the user is registered
                    if message_type == 'chat':
                        self.chat_module.handle_message(username, message)

                    elif message_type == 'file_upload_request': # Renamed for clarity
                        self.file_module.handle_upload(username, message, client_socket)
                    elif message_type == 'file_data_chunk': # Added to handle file chunks
                         self.file_module.handle_file_data(username, message, client_socket)
                    elif message_type == 'file_download_request': # Renamed for clarity
                        self.file_module.handle_download(username, message, client_socket)

                    elif message_type == 'screen_share_start':
                        self.screen_share_module.start_presentation(username, message)
                    elif message_type == 'screen_share_stop':
                        self.screen_share_module.stop_presentation(username)
                    elif message_type == 'screen_frame':
                        self.screen_share_module.handle_frame(username, message, client_socket)
                    # Add handlers for other message types here (e.g., video/audio control)
                    else:
                        log_warning(f"Received unknown message type '{message_type}' from {username}")

                else:
                    # Received a message other than 'register' before successful registration
                    log_warning(f"Received message type '{message_type}' from unregistered client {client_address}. Closing connection.")
                    self.send_error(client_socket, "Please register first.")
                    break

        except ConnectionResetError:
             log_event(f"Client {client_address} (User: {username or 'Unregistered'}) disconnected abruptly.")
        except Exception as e:
            # Log unexpected errors during handling
            log_error(f"Error handling client {client_address} (User: {username or 'Unregistered'}): {e}")
            print(f"❌ Error with client {username or client_address}: {e}")
        finally:
            # Ensure cleanup happens regardless of how the loop exits
            if username:
                self.unregister_client(username)
            try:
                client_socket.close()
                log_event(f"Closed socket for {client_address} (User: {username or 'Disconnected'})")
            except Exception as e_close:
                 log_error(f"Error closing client socket for {client_address}: {e_close}")

    def register_client(self, username, client_socket, client_address, video_udp_port=None, audio_udp_port=None):
        """Registers a new client (Assumes called within self.clients_lock)"""
        video_udp_addr = (client_address[0], video_udp_port) if video_udp_port else None
        audio_udp_addr = (client_address[0], audio_udp_port) if audio_udp_port else None

        self.clients[username] = {
            'socket': client_socket,
            'address': client_address,
            'status': 'online',
            'video_udp_addr': video_udp_addr,
            'audio_udp_addr': audio_udp_addr,
            'joined_at': datetime.now()
        }

        # Update modules with UDP info
        if video_udp_addr:
            self.video_module.set_client_udp_address(username, video_udp_addr)
        if audio_udp_addr:
            self.audio_module.set_client_udp_address(username, audio_udp_addr)

        # Send registration confirmation
        response = {
            'type': 'registration_success',
            'username': username,
            'server_time': datetime.now().isoformat()
        }
        if not self.send_to_client(username, response, acquire_lock=False): # Already holding lock
             # Failed to send confirmation, registration incomplete, clean up
             log_error(f"Failed to send registration confirmation to {username}. Aborting registration.")
             del self.clients[username]
             client_socket.close() # Close the socket immediately
             return # Don't proceed with broadcasts

        # Notify other clients (outside the lock to avoid potential deadlocks if send_to_client waits)
        # However, sending requires accessing self.clients, so we need a careful approach.
        # Option 1: Release lock, do broadcasts, re-acquire if needed (risk of race conditions).
        # Option 2: Get list of recipients first, release lock, then send. (Chosen here)
        current_clients = list(self.clients.keys()) # Get recipients while holding lock

        # Drop the lock before broadcasting to avoid deadlocks
        # (Technically, register_client itself is called *within* the lock in handle_client)
        # So, these broadcasts should happen *after* register_client returns in handle_client.
        # --- Let's refactor handle_client slightly ---
        # *** See adjusted handle_client where broadcasts happen after lock release ***

        log_event(f"User '{username}' registered from {client_address}")
        print(f"✅ User '{username}' registered successfully")


        # --- Refactored handle_client ---
    def handle_client(self, client_socket, client_address):
        """Handle individual client communication using framed messages"""
        username = None
        registered_successfully = False
        try:
            while self.running:
                message = receive_framed_message(client_socket)
                if message is None:
                    break # Connection issue

                message_type = message.get('type')

                if message_type == 'register' and not registered_successfully:
                    temp_username = message.get('username')
                    video_udp_port = message.get('video_udp_port')
                    audio_udp_port = message.get('audio_udp_port')
                    is_valid_user = temp_username and isinstance(temp_username, str) and 3 <= len(temp_username) <= 20

                    registration_success = False
                    with self.clients_lock:
                        if is_valid_user and temp_username not in self.clients:
                            self.register_client(temp_username, client_socket, client_address, video_udp_port, audio_udp_port)
                            username = temp_username # Assign username *after* successful registration call
                            registration_success = True
                            registered_successfully = True # Mark registration complete for this handler
                        elif not is_valid_user:
                             self.send_error(client_socket, "Invalid username format (3-20 alphanumeric chars).")
                             log_warning(f"Reg failed {client_address}: Invalid username '{temp_username}'")
                             break
                        else:
                            self.send_error(client_socket, f"Username '{temp_username}' already taken.")
                            log_warning(f"Reg failed {client_address}: Username '{temp_username}' taken.")
                            break

                    # Broadcasts happen *outside* the lock
                    if registration_success:
                        self.broadcast_user_list()
                        self.chat_module.broadcast_system_message(f"{username} joined the session")

                elif registered_successfully and username: # User is registered
                    # ... (handle other message types as before) ...
                     if message_type == 'chat':
                         self.chat_module.handle_message(username, message)
                     elif message_type == 'file_upload_request':
                         self.file_module.handle_upload(username, message, client_socket)
                     elif message_type == 'file_data_chunk':
                          self.file_module.handle_file_data(username, message, client_socket)
                     elif message_type == 'file_download_request':
                         self.file_module.handle_download(username, message, client_socket)
                     elif message_type == 'screen_share_start':
                         self.screen_share_module.start_presentation(username, message)
                     elif message_type == 'screen_share_stop':
                         self.screen_share_module.stop_presentation(username)
                     elif message_type == 'screen_frame':
                         self.screen_share_module.handle_frame(username, message, client_socket)
                     else:
                         log_warning(f"Received unknown message type '{message_type}' from {username}")

                elif not registered_successfully:
                    log_warning(f"Received '{message_type}' from unregistered {client_address}. Closing.")
                    self.send_error(client_socket, "Please register first.")
                    break
        # ... (rest of the try...except...finally block as before) ...
        except ConnectionResetError:
             log_event(f"Client {client_address} (User: {username or 'Unregistered'}) disconnected abruptly.")
        except Exception as e:
            log_error(f"Error handling client {client_address} (User: {username or 'Unregistered'}): {e} ({type(e).__name__})")
            print(f"❌ Error with client {username or client_address}: {e}")
        finally:
            if username:
                self.unregister_client(username) # This also needs locking
            try:
                client_socket.close()
                log_event(f"Closed socket for {client_address} (User: {username or 'Disconnected'})")
            except Exception as e_close:
                 log_error(f"Error closing client socket for {client_address}: {e_close}")


    # Refined register_client (only does the dictionary update and confirmation send)
    def register_client(self, username, client_socket, client_address, video_udp_port=None, audio_udp_port=None):
        """Registers client data (Assumes called within self.clients_lock)"""
        video_udp_addr = (client_address[0], video_udp_port) if video_udp_port else None
        audio_udp_addr = (client_address[0], audio_udp_port) if audio_udp_port else None

        self.clients[username] = {
            'socket': client_socket, 'address': client_address, 'status': 'online',
            'video_udp_addr': video_udp_addr, 'audio_udp_addr': audio_udp_addr,
            'joined_at': datetime.now()
        }

        # Update modules - these calls should be thread-safe or handle internal locking if needed
        if video_udp_addr: self.video_module.set_client_udp_address(username, video_udp_addr)
        if audio_udp_addr: self.audio_module.set_client_udp_address(username, audio_udp_addr)

        # Send confirmation
        response = {'type': 'registration_success', 'username': username, 'server_time': datetime.now().isoformat()}
        # Use a non-locking send variant if called from within lock, or ensure send_framed_message handles it
        if not send_framed_message(client_socket, response): # Use helper directly
             log_error(f"Failed sending reg confirmation to {username}.")
             # Clean up immediately since registration failed mid-way
             if video_udp_addr: self.video_module.set_client_udp_address(username, None) # Revert module update
             if audio_udp_addr: self.audio_module.set_client_udp_address(username, None) # Revert module update
             del self.clients[username]
             # Don't close socket here, let the caller handle it upon failure return
             return False # Indicate failure

        log_event(f"User '{username}' registered from {client_address}")
        print(f"✅ User '{username}' registered successfully")
        return True # Indicate success


    def unregister_client(self, username):
        """Unregister a client (Handles locking)"""
        client_info = None
        with self.clients_lock:
            if username in self.clients:
                client_info = self.clients.pop(username) # Remove client atomically

        if client_info: # Only proceed if client was actually removed
            log_event(f"User '{username}' disconnected")
            print(f"🔌 User '{username}' disconnected")

            # If this user was presenting, stop presentation
            # Check needs to be thread-safe if current_presenter can be modified elsewhere
            # Assuming simple check for now, might need a lock around presenter status too
            if self.screen_share_module.current_presenter == username:
                 self.screen_share_module.stop_presentation(username) # This likely broadcasts

            # Notify remaining clients (outside the lock)
            self.broadcast_user_list()
            self.chat_module.broadcast_system_message(f"{username} left the session")

            # Clean up UDP addresses in modules
            if client_info.get('video_udp_addr'):
                self.video_module.set_client_udp_address(username, None) # Notify module client is gone
            if client_info.get('audio_udp_addr'):
                 self.audio_module.set_client_udp_address(username, None) # Notify module client is gone
        else:
             log_warning(f"Attempted to unregister non-existent user: {username}")


    def send_to_client(self, username, message, acquire_lock=True):
        """Send message to specific client using framed helper (Handles locking)"""
        client_socket = None
        if acquire_lock:
            with self.clients_lock:
                client_info = self.clients.get(username)
                if client_info:
                    client_socket = client_info['socket']
        else:
            # Assumes caller is already holding the lock
             client_info = self.clients.get(username)
             if client_info:
                 client_socket = client_info['socket']

        if client_socket:
            if send_framed_message(client_socket, message):
                return True
            else:
                # Send failed, client might be disconnected
                log_warning(f"Failed to send message to {username}. Might disconnect.")
                # Consider initiating disconnect procedure here if send fails repeatedly
                return False
        else:
            # Client not found (or lock wasn't held correctly if acquire_lock=False)
            if acquire_lock: # Only log if we expected to find the client
                log_warning(f"Attempted to send message to non-existent user: {username}")
            return False

    def broadcast_to_all(self, message, exclude_username=None):
        """Broadcast message to all connected clients (Handles locking)"""
        # Get a snapshot of recipients under the lock to avoid issues if clients dict changes during iteration
        recipients = []
        with self.clients_lock:
            recipients = list(self.clients.keys())

        for username in recipients:
            if username != exclude_username:
                # send_to_client handles its own locking internally now
                self.send_to_client(username, message)

    def broadcast_user_list(self):
        """Broadcast updated user list to all clients (Handles locking)"""
        user_list_data = []
        current_presenter_snapshot = self.screen_share_module.current_presenter # Get presenter status (assuming thread-safe read or infrequent change)

        with self.clients_lock:
            for username, client_data in self.clients.items():
                user_list_data.append({
                    'username': username,
                    'status': client_data.get('status', 'offline'),
                    'joined_at': client_data.get('joined_at', datetime.now()).isoformat() # Provide default
                })

        message = {
            'type': 'user_list_update',
            'users': user_list_data,
            'current_presenter': current_presenter_snapshot # Include who is presenting
        }
        self.broadcast_to_all(message) # Broadcast uses the locked send_to_client

    def send_error(self, client_socket, error_message):
        """Send error message to a client socket using framed helper"""
        error_msg = {
            'type': 'error',
            'message': error_message
        }
        # Use helper directly, don't need username lookup here
        if not send_framed_message(client_socket, error_msg):
             log_warning(f"Failed to send error message to {client_socket.getpeername()}")


    def stop_server(self):
        """Stop the server and cleanup"""
        if not self.running:
             return # Already stopped or stopping

        print("🔌 Stopping server...")
        log_event("Server shutdown requested.")
        self.running = False # Signal loops to stop

        # Stop modules first (they might rely on sockets)
        try: self.video_module.stop()
        except Exception as e: log_error(f"Error stopping video module: {e}")
        try: self.audio_module.stop()
        except Exception as e: log_error(f"Error stopping audio module: {e}")
        try: self.chat_module.stop()
        except Exception as e: log_error(f"Error stopping chat module: {e}")
        try: self.file_module.stop()
        except Exception as e: log_error(f"Error stopping file module: {e}")
        try: self.screen_share_module.stop()
        except Exception as e: log_error(f"Error stopping screen share module: {e}")


        # Close server sockets
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
                log_event("Closed TCP server socket.")
            except Exception as e: log_error(f"Error closing TCP socket: {e}")
        if self.video_udp_socket:
             try:
                 self.video_udp_socket.close()
                 log_event("Closed Video UDP server socket.")
             except Exception as e: log_error(f"Error closing Video UDP socket: {e}")
        if self.audio_udp_socket:
             try:
                 self.audio_udp_socket.close()
                 log_event("Closed Audio UDP server socket.")
             except Exception as e: log_error(f"Error closing Audio UDP socket: {e}")

        # Close all remaining client connections
        with self.clients_lock:
            usernames = list(self.clients.keys()) # Get list before iterating
            for username in usernames:
                client_info = self.clients.pop(username, None)
                if client_info and client_info.get('socket'):
                    try:
                         client_info['socket'].close()
                         log_event(f"Closed connection for {username} during shutdown.")
                    except Exception as e_close:
                         log_error(f"Error closing socket for {username} during shutdown: {e_close}")

        print("✅ Server stopped.")
        log_event("Server stopped.")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='LAN Communication Server')
    parser.add_argument('host', nargs='?', default='0.0.0.0',
                        help='Server IP address (default: 0.0.0.0 - listens on all interfaces)')
    parser.add_argument('port', nargs='?', type=int, default=5000,
                        help='Server port for TCP connections (default: 5000)')

    args = parser.parse_args()

    print("🚀 LAN Communication Server")
    print("=" * 50)

    # Create and start server
    server = LANCommunicationServer(args.host, args.port)

    try:
        # Start server blocks until KeyboardInterrupt or error
        server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        server.stop_server()
    except Exception as e:
        print(f"❌ Server encountered a fatal error: {e}")
        log_error(f"Server fatal error: {e}", exc_info=True) # Log traceback
        server.stop_server()

if __name__ == "__main__":
    main()
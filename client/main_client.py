#!/usr/bin/env python3
"""
LAN Communication Client - Main Client Controller
Connects to server and manages all communication modules
(Modified with TCP Message Framing, GUI queue integration, and send_tcp fix)
"""

import socket
import threading
import json
import sys
import os
import time
from datetime import datetime
import queue # Import queue for GUI updates
import traceback # For detailed error logging

# Add client directory to path for imports
# Ensure this works correctly based on how you run the script
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir) # Add current script's directory
# If utils.py is in the same directory, this should work:
try:
    from utils import send_framed_message, receive_framed_message
except ImportError:
    print("❌ Critical Error: Could not import 'send_framed_message' or 'receive_framed_message'.")
    print("   Ensure 'utils.py' exists in the same directory as 'main_client.py'.")
    sys.exit(1)


# Import module classes (assuming they are in the same directory or path is set)
try:
    from video_client import VideoClient
    from audio_client import AudioClient
    from chat_client import ChatClient
    from file_client import FileClient
    from screen_share_client import ScreenShareClient
    # Ensure ui directory is accessible
    from ui.main_window import MainWindow
except ImportError as e:
    print(f"❌ Critical Import Error: {e}. Make sure all module files exist and paths are correct.")
    sys.exit(1)


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
        self.video_local_port = 0 # Store chosen UDP ports
        self.audio_local_port = 0

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

        # Queue for thread-safe GUI updates
        self.gui_update_queue = queue.Queue()


    def connect_to_server(self, username):
        """Connect to the server and register"""
        try:
            # Basic username validation
            if not username or not (3 <= len(username) <= 20):
                 print("❌ Invalid username (must be 3-20 characters).")
                 return False

            print(f"Attempting to connect to {self.server_host}:{self.server_port}...")
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set a timeout for the connection attempt
            self.tcp_socket.settimeout(5.0)
            self.tcp_socket.connect((self.server_host, self.server_port))
            self.tcp_socket.settimeout(None) # Remove timeout after connection
            print("✅ TCP connection successful.")

            # Create UDP sockets
            self.video_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.audio_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Allow socket reuse (less critical for clients but doesn't hurt)
            self.video_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.audio_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind UDP sockets to local ports (let OS choose)
            self.video_udp_socket.bind(('', 0))
            self.audio_udp_socket.bind(('', 0))

            # Get the actual bound ports
            self.video_local_port = self.video_udp_socket.getsockname()[1]
            self.audio_local_port = self.audio_udp_socket.getsockname()[1]

            print(f"📹 Video UDP bound to local port: {self.video_local_port}")
            print(f"🎵 Audio UDP bound to local port: {self.audio_local_port}")

            # Register with server using framed message
            self.username = username
            registration = {
                'type': 'register',
                'username': username,
                'client_time': datetime.now().isoformat(),
                'video_udp_port': self.video_local_port,
                'audio_udp_port': self.audio_local_port
            }
            # ** The send_tcp_message now uses the corrected check **
            if not self.send_tcp_message(registration):
                 print("❌ Failed to send registration message.")
                 self.disconnect() # Clean up sockets
                 return False
            print("⏳ Registration message sent, waiting for confirmation...")

            # Wait for registration confirmation (using framed receive)
            # Add a timeout for receiving the confirmation
            self.tcp_socket.settimeout(10.0) # Wait up to 10 seconds for response
            response = receive_framed_message(self.tcp_socket)
            self.tcp_socket.settimeout(None) # Remove timeout

            if response and response.get('type') == 'registration_success':
                self.connected = True # Set connected flag *after* confirmation
                self.running = True
                print(f"✅ Successfully registered as '{username}'")

                # Start receive thread AFTER successful registration
                self.receive_thread = threading.Thread(target=self.receive_loop, name="TCPReceiveThread", daemon=True)
                self.receive_thread.start()

                # Initialize modules (which might start more threads)
                self.initialize_modules() # Make sure this doesn't block GUI startup

                print(f"✅ Modules initialized. Client is running.")
                return True
            elif response and response.get('type') == 'error':
                 print(f"❌ Registration failed: {response.get('message', 'Unknown server error')}")
                 self.disconnect()
                 return False
            else:
                print(f"❌ Registration failed: No valid response from server. (Received: {response})")
                self.disconnect()
                return False

        except socket.timeout:
             print(f"❌ Connection timed out attempting to reach {self.server_host}:{self.server_port}")
             self.disconnect()
             return False
        except ConnectionRefusedError:
              print(f"❌ Connection refused by server {self.server_host}:{self.server_port}. Is the server running?")
              self.disconnect()
              return False
        except Exception as e:
            print(f"❌ Connection failed: {e} ({type(e).__name__})")
            traceback.print_exc() # Print full traceback for debugging
            self.disconnect() # Clean up if connection fails
            return False

    def initialize_modules(self):
        """Initialize all client modules"""
        print("⏳ Initializing modules...")
        self.video_client = VideoClient(self)
        self.audio_client = AudioClient(self)
        self.chat_client = ChatClient(self)
        self.file_client = FileClient(self)
        self.screen_share_client = ScreenShareClient(self)

        # IMPORTANT: Initialize GUI last. It needs access to other modules.
        # The GUI (MainWindow) should be run in the main thread later.
        self.main_window = MainWindow(self)
        # Pass the queue to the MainWindow instance for thread-safe updates
        self.main_window.gui_update_queue = self.gui_update_queue

        # Start background threads for UDP listening AFTER modules are created
        self.video_thread = threading.Thread(target=self.video_loop, name="VideoUDPThread", daemon=True)
        self.audio_thread = threading.Thread(target=self.audio_loop, name="AudioUDPThread", daemon=True)

        self.video_thread.start()
        self.audio_thread.start()
        print("✅ Background network threads started.")

    def receive_loop(self):
        """Main receive loop for TCP messages using framed messages"""
        print("TCP receive loop started.")
        while self.running and self.connected:
            if not self.tcp_socket: # Safety check
                 print("TCP receive loop: Socket is None, stopping.")
                 break
            message = receive_framed_message(self.tcp_socket)

            if message is None:
                # receive_framed_message returning None indicates a connection issue or closure
                if self.running: # Avoid error message if we initiated the disconnect
                    print("❌ Connection lost with server.")
                    # Use the queue to signal the GUI/main thread about the disconnection
                    if hasattr(self, 'gui_update_queue') and self.gui_update_queue:
                         self.gui_update_queue.put({'type': 'connection_lost'})
                break # Exit the loop

            # Put received message onto the GUI queue for safe handling in the main thread
            # print(f"DEBUG: Received TCP message: {message.get('type')}") # Debug print
            if hasattr(self, 'gui_update_queue') and self.gui_update_queue:
                 self.gui_update_queue.put(message)

        # --- Loop finished ---
        # Ensure flags are set correctly if the loop exits unexpectedly
        is_still_running = self.running # Store state before potentially changing it
        self.running = False
        self.connected = False
        print("TCP receive loop stopped.")
        # Signal connection lost if not already done and if shutdown wasn't intentional
        if is_still_running and hasattr(self, 'gui_update_queue') and self.gui_update_queue:
            try:
                 self.gui_update_queue.put({'type': 'connection_lost'})
            except Exception as e:
                 print(f"Error signalling connection lost via queue: {e}")


    def handle_server_message(self, message):
        """Handle incoming message from server (Called by GUI thread via queue)"""
        # This function is now executed IN THE MAIN/GUI THREAD.
        message_type = message.get('type')
        # print(f"GUI Thread Processing: {message_type}") # Uncomment for intense debugging

        try:
            if message_type == 'user_list_update':
                if self.main_window:
                    self.main_window.update_user_list(message.get('users', []))

            elif message_type == 'chat_message':
                if self.chat_client:
                    self.chat_client.handle_message(message.get('data'))
                    if self.main_window: self.main_window.update_chat_display() # Trigger redraw

            elif message_type == 'system_message':
                if self.chat_client:
                    self.chat_client.handle_system_message(message.get('data'))
                    if self.main_window: self.main_window.update_chat_display() # Trigger redraw

            elif message_type == 'file_available':
                if self.file_client:
                    self.file_client.handle_file_available(message.get('file_info'))
                    # file_client->handle_file_available should call main_window.update_file_list

            # --- Handle File Transfer Data ---
            elif message_type == 'upload_confirmed':
                 file_id = message.get('file_id')
                 print(f"Server confirmed upload for file ID: {file_id}")
                 # File client needs a method to start sending file chunks in a background thread
                 if self.file_client and hasattr(self.file_client, 'start_sending_file'):
                      # This should start a new thread within file_client
                      threading.Thread(target=self.file_client.start_sending_file, args=(file_id,), daemon=True).start()
                 else:
                      print("WARNING: file_client.start_sending_file method not found!")

            elif message_type == 'upload_progress':
                 progress = message.get('progress', 0)
                 if self.main_window and hasattr(self.main_window, 'progress_var') and self.main_window.progress_var:
                      self.main_window.progress_var.set(progress)

            elif message_type == 'file_data_start':
                 if self.file_client: self.file_client.handle_file_data_start(message)
            elif message_type == 'file_data_chunk':
                 if self.file_client: self.file_client.handle_file_data_chunk(message)
            elif message_type == 'file_data_complete':
                 if self.file_client: self.file_client.handle_file_data_complete(message)

            # --- Screen Share ---
            elif message_type == 'presentation_started':
                if self.screen_share_client:
                    self.screen_share_client.handle_presentation_started(message)
                    if self.main_window: self.main_window.update_screen_share_display()

            elif message_type == 'presentation_stopped':
                if self.screen_share_client:
                    self.screen_share_client.handle_presentation_stopped(message)
                    if self.main_window: self.main_window.update_screen_share_display()

            elif message_type == 'screen_frame':
                if self.screen_share_client:
                    self.screen_share_client.handle_screen_frame(message)
                    # GUI update is likely handled by main_window polling or triggered internally

            elif message_type == 'error':
                error_msg = message.get('message', 'Unknown server error')
                print(f"❌ Server Error: {error_msg}")
                if self.main_window and self.main_window.root:
                    self.main_window.root.after(0, lambda msg=error_msg:
                        self.main_window.messagebox.showerror("Server Error", msg)
                    )

            # --- Connection Lost Signal (from receive_loop) ---
            elif message_type == 'connection_lost':
                 print("🔌 Connection lost detected by main thread.")
                 if self.connected: # Only act if we thought we were connected
                     self.connected = False
                     self.running = False
                     if self.main_window:
                          self.main_window.running = False # Stop GUI queue check
                          self.main_window.status_label.config(text="Disconnected - Connection Lost")
                          self.main_window.root.after(0, lambda:
                               self.main_window.messagebox.showerror("Connection Error", "Lost connection to the server.")
                          )
                     # No need to call self.disconnect() here, run() finally block handles it

            else:
                print(f"⚠️ Received unhandled message type: {message_type}")

        except Exception as e:
            print(f"❌ Error handling server message (type: {message_type}): {e}")
            traceback.print_exc()


    def video_loop(self):
        """Video processing loop (UDP Receive)"""
        print("Video UDP receive loop started.")
        while self.running and self.connected and self.video_udp_socket:
            try:
                self.video_udp_socket.settimeout(1.0)
                data, addr = self.video_udp_socket.recvfrom(65536)

                if len(data) > 8:
                    import struct
                    try:
                        username_len = struct.unpack('!I', data[:4])[0]
                        if username_len > 1024 or 4 + username_len >= len(data):
                             # print(f"⚠️ Invalid video packet from {addr} (bad username length: {username_len}, size: {len(data)})")
                             continue

                        username = data[4:4+username_len].decode('utf-8', errors='ignore')
                        frame_data = data[4+username_len:]

                        if self.video_client:
                             self.video_client.handle_received_frame(username, frame_data)

                    except struct.error: pass # Ignore unpack errors silently for UDP? Maybe log occasionally.
                    except UnicodeDecodeError: pass # Ignore username decode errors
                    except IndexError: pass # Ignore index errors

            except socket.timeout:
                continue
            except socket.error as e:
                 # Ignore certain errors like ConnectionResetError (WSAECONNRESET on Windows) for UDP
                 if hasattr(e, 'winerror') and e.winerror == 10054:
                      pass # Connection reset by peer - common for UDP if peer closes
                 elif e.errno == 101: # Network unreachable
                      print("⚠️ Video UDP: Network unreachable.")
                      if self.running: self.gui_update_queue.put({'type': 'connection_lost'})
                      break
                 else:
                     print(f"⚠️ Video UDP socket error: {e}")
                 if not self.running: break
                 time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"❌ Video UDP loop error: {e} ({type(e).__name__})")
                if not self.running: break
                time.sleep(0.01)

        print("Video UDP receive loop stopped.")


    def audio_loop(self):
        """Audio processing loop (UDP Receive)"""
        print("Audio UDP receive loop started.")
        while self.running and self.connected and self.audio_udp_socket:
            try:
                self.audio_udp_socket.settimeout(1.0)
                data, addr = self.audio_udp_socket.recvfrom(4096) # Audio packets usually smaller

                if len(data) > 8:
                    import struct
                    try:
                        user_count = struct.unpack('!I', data[:4])[0]
                        if user_count > 100 or user_count < 0:
                             continue # Invalid count

                        offset = 4
                        usernames = []
                        valid_packet = True
                        for _ in range(user_count):
                            username_end = data.find(b'\x00', offset)
                            if username_end == -1 or username_end >= len(data) - 1:
                                 valid_packet = False; break
                            uname_bytes = data[offset:username_end]
                            if len(uname_bytes) > 50: # Max username length check
                                valid_packet = False; break
                            usernames.append(uname_bytes.decode('utf-8', errors='ignore'))
                            offset = username_end + 1

                        if valid_packet and offset < len(data):
                             audio_data = data[offset:]
                             if self.audio_client:
                                 self.audio_client.handle_mixed_audio(audio_data, usernames)

                    except struct.error: pass # Ignore unpack errors
                    except UnicodeDecodeError: pass # Ignore username errors
                    except IndexError: pass # Ignore index errors

            except socket.timeout:
                continue
            except socket.error as e:
                 if hasattr(e, 'winerror') and e.winerror == 10054: pass
                 elif e.errno == 101: # Network unreachable
                      print("⚠️ Audio UDP: Network unreachable.")
                      if self.running: self.gui_update_queue.put({'type': 'connection_lost'})
                      break
                 else:
                     print(f"⚠️ Audio UDP socket error: {e}")
                 if not self.running: break
                 time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"❌ Audio UDP loop error: {e} ({type(e).__name__})")
                if not self.running: break
                time.sleep(0.01)
        print("Audio UDP receive loop stopped.")


    def send_tcp_message(self, message):
        """Send TCP message to server using framed helper (Corrected Check)"""
        # Allow sending if socket exists, even if not fully 'connected' yet (for registration)
        if not self.tcp_socket:
            print("❌ Cannot send TCP message: TCP socket does not exist.")
            return False

        success = send_framed_message(self.tcp_socket, message) # Assumes utils.py has send_framed_message
        if not success:
            # If send fails, the connection might be broken. Signal this via queue.
             print("❌ Failed to send TCP message. Connection may be lost.")
             if hasattr(self, 'gui_update_queue') and self.gui_update_queue:
                  # Avoid potential deadlock if queue is full? Use put_nowait?
                  try: self.gui_update_queue.put_nowait({'type': 'connection_lost'})
                  except queue.Full: print("GUI queue full, cannot signal connection lost.")
             # Update state immediately? Could lead to race conditions. Let queue handle it.
             # self.connected = False
             # self.running = False
        return success


    def receive_tcp_message(self):
        """DEPRECATED - Use receive_loop instead. Kept for initial reg check."""
        if not self.tcp_socket: return None
        return receive_framed_message(self.tcp_socket)


    def send_video_frame(self, frame_data):
        """Send video frame to server via UDP"""
        if not self.connected or not self.username or not self.video_udp_socket:
            return
        try:
            import struct
            username_bytes = self.username.encode('utf-8')
            header = struct.pack('!I', len(username_bytes))
            packet = header + username_bytes + frame_data
            if len(packet) > 65500:
                 print(f"⚠️ Video packet too large ({len(packet)} bytes), might be dropped.")
                 # Consider alternatives: reduce quality/resolution, or implement fragmentation
                 return # Don't send oversized packets

            self.video_udp_socket.sendto(packet, (self.server_host, self.server_port + 1))
        except socket.error as e:
             # Ignore certain errors like host unreachable if connection is dropping
             if e.errno == 113: # EHOSTUNREACH
                  pass # Silently ignore if host becomes unreachable?
             elif hasattr(e, 'winerror') and e.winerror == 10051: # Network Unreachable (Windows)
                  pass
             else:
                 print(f"❌ Socket error sending video frame: {e}")
             # Signal connection lost if specific errors occur?
             # if e.errno in [101, 113] and self.running: self.gui_update_queue.put({'type': 'connection_lost'})
        except Exception as e:
            print(f"❌ Error sending video frame: {e}")


    def send_audio_data(self, audio_data):
        """Send audio data to server via UDP"""
        if not self.connected or not self.username or not self.audio_udp_socket:
            return
        try:
            import struct
            username_bytes = self.username.encode('utf-8')
            header = struct.pack('!I', len(username_bytes))
            packet = header + username_bytes + audio_data
            # Audio packets are smaller, less likely to exceed limits
            self.audio_udp_socket.sendto(packet, (self.server_host, self.server_port + 2))
        except socket.error as e:
             if e.errno == 113 or (hasattr(e, 'winerror') and e.winerror == 10051): pass
             else: print(f"❌ Socket error sending audio data: {e}")
             # if e.errno in [101, 113] and self.running: self.gui_update_queue.put({'type': 'connection_lost'})
        except Exception as e:
            print(f"❌ Error sending audio data: {e}")

    # --- Methods to send specific commands (using send_tcp_message) ---

    def send_chat_message(self, message):
        """Send chat message command to server"""
        chat_msg = {'type': 'chat', 'message': message}
        return self.send_tcp_message(chat_msg) # Return success status

    def send_file_upload_request(self, filename, file_size, file_hash):
        """Send file upload request command to server"""
        upload_req = {
            'type': 'file_upload_request',
            'filename': filename, 'file_size': file_size, 'file_hash': file_hash
        }
        return self.send_tcp_message(upload_req)

    def send_file_data_chunk(self, file_id, chunk_index, chunk_data_hex):
         """Sends a chunk of file data during upload."""
         chunk_msg = {
              'type': 'file_data_chunk',
              'file_id': file_id,
              'chunk_index': chunk_index,
              'chunk_data': chunk_data_hex
         }
         # This needs to be robust - handle potential send failures and retries?
         return self.send_tcp_message(chunk_msg)

    def send_file_download_request(self, file_id):
        """Send file download request command to server"""
        download_req = {'type': 'file_download_request', 'file_id': file_id}
        return self.send_tcp_message(download_req)

    def start_screen_sharing(self):
        """Send start screen sharing command to server"""
        share_req = {'type': 'screen_share_start', 'timestamp': datetime.now().isoformat()}
        return self.send_tcp_message(share_req)

    def stop_screen_sharing(self):
        """Send stop screen sharing command to server"""
        stop_req = {'type': 'screen_share_stop', 'timestamp': datetime.now().isoformat()}
        return self.send_tcp_message(stop_req)

    def send_screen_frame(self, frame_data_b64, frame_format='jpeg'):
         """Sends a captured screen frame via TCP."""
         frame_msg = {
              'type': 'screen_frame',
              'frame_data': frame_data_b64,
              'format': frame_format,
              'timestamp': time.time()
         }
         return self.send_tcp_message(frame_msg)


    def disconnect(self):
        """Disconnect from server and clean up resources"""
        if not self.running and not self.connected:
             return

        print("🔌 Disconnecting client...")
        self.running = False # Signal threads to stop FIRST
        self.connected = False

        # Stop modules (add try-except around each)
        try:
             if self.video_client: self.video_client.stop_camera()
        except Exception as e: print(f"Error stopping video client: {e}")
        try:
             if self.audio_client: self.audio_client.stop_audio(); self.audio_client.cleanup()
        except Exception as e: print(f"Error stopping audio client: {e}")
        try:
             if self.chat_client and hasattr(self.chat_client, 'stop'): self.chat_client.stop()
        except Exception as e: print(f"Error stopping chat client: {e}")
        try:
            if self.screen_share_client: self.screen_share_client.stop_sharing()
        except Exception as e: print(f"Error stopping screen share client: {e}")
        # Add file_client stop if needed

        # --- Gracefully close sockets ---
        # TCP Socket
        sock_tcp = self.tcp_socket
        self.tcp_socket = None
        if sock_tcp:
            try:
                sock_tcp.shutdown(socket.SHUT_RDWR) # Signal closure
                sock_tcp.close()
                print("TCP socket closed.")
            except socket.error as e:
                if e.errno not in [107, 9]: # ENOTCONN (107), EBADF (9) - already closed/invalid
                     print(f"Error closing TCP socket: {e}")
            except Exception as e: print(f"Unexpected error closing TCP socket: {e}")

        # Video UDP Socket
        sock_vid_udp = self.video_udp_socket
        self.video_udp_socket = None
        if sock_vid_udp:
            try: sock_vid_udp.close(); print("Video UDP socket closed.")
            except Exception as e: print(f"Error closing Video UDP socket: {e}")

        # Audio UDP Socket
        sock_aud_udp = self.audio_udp_socket
        self.audio_udp_socket = None
        if sock_aud_udp:
            try: sock_aud_udp.close(); print("Audio UDP socket closed.")
            except Exception as e: print(f"Error closing Audio UDP socket: {e}")

        # --- Wait for threads to potentially finish ---
        # Joining daemon threads isn't strictly necessary, but can be cleaner
        # If threads aren't daemons, you MUST join them.
        # Example joining with timeout (optional for daemon threads):
        # thread_timeout = 1.0 # seconds
        # if self.receive_thread and self.receive_thread.is_alive(): self.receive_thread.join(thread_timeout)
        # if self.video_thread and self.video_thread.is_alive(): self.video_thread.join(thread_timeout)
        # if self.audio_thread and self.audio_thread.is_alive(): self.audio_thread.join(thread_timeout)

        print("Client disconnected.")


    def run(self):
        """Run the client application: Connect and start GUI"""
        try:
            # Get username interactively
            while True:
                username = input("Enter your username (3-20 chars): ").strip()
                if 3 <= len(username) <= 20:
                    break
                print("Invalid username. Please try again.")

            # Connect to server (initializes modules on success)
            if not self.connect_to_server(username):
                print("❌ Exiting: Could not connect to the server.")
                return # Exit if connection fails

            # --- Start GUI ---
            if self.main_window:
                print("Starting GUI...")
                self.main_window.run() # This call blocks until the GUI window is closed
                print("GUI finished.")
            else:
                 print("❌ GUI could not be initialized.")

        except KeyboardInterrupt:
            print("\n🛑 Shutting down client (Ctrl+C pressed)...")
        except Exception as e:
            print(f"❌ Client encountered a fatal error: {e}")
            traceback.print_exc() # Print stack trace for debugging
        finally:
            # Ensure disconnect is called when run() finishes, errors out, or Ctrl+C is caught
            self.disconnect()

# --- Main Execution ---
def main():
    """Main entry point"""
    print("🚀 LAN Communication Client")
    print("=" * 50)

    # Get server connection info interactively
    default_host = 'localhost'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        default_host = local_ip
    except Exception: pass

    server_host = input(f"Enter server IP (e.g., {default_host}): ").strip() or default_host

    default_port = 5000
    while True:
        port_str = input(f"Enter server port (default: {default_port}): ").strip() or str(default_port)
        try:
            server_port = int(port_str)
            if 1 <= server_port <= 65535: break
            else: print("Port must be between 1 and 65535.")
        except ValueError: print("Invalid port number. Please enter an integer.")

    # Create and run client
    client = LANCommunicationClient(server_host, server_port)
    client.run()

if __name__ == "__main__":
    main()
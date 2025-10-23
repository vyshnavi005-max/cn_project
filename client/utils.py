#!/usr/bin/env python3
"""
Utilities for the LAN Communication Client
(Including TCP Message Framing Helpers)
"""

import json
import struct
import socket

# Helper to send a framed message
def send_framed_message(sock, message_dict):
    """Sends a JSON message prefixed with its length."""
    if not sock:
        print("❌ Cannot send message: Socket is not connected.")
        return False
    try:
        message_json = json.dumps(message_dict).encode('utf-8')
        message_len = len(message_json)
        # Pack the length into 4 bytes (unsigned integer, network byte order)
        header = struct.pack('!I', message_len)
        sock.sendall(header + message_json) # Send header then message
        return True
    except socket.error as e:
        print(f"❌ Socket error sending framed message: {e}")
        # Consider notifying the main client to handle disconnection
        return False
    except Exception as e:
        print(f"❌ Error sending framed message: {e}")
        return False

# Helper to receive a framed message
def receive_framed_message(sock):
    """Receives a length-prefixed JSON message."""
    if not sock:
        print("❌ Cannot receive message: Socket is not connected.")
        return None
    try:
        # Read the 4-byte header first
        header_data = sock.recv(4)
        if not header_data:
            print("🔌 Connection closed by server (received empty header).")
            return None
        if len(header_data) < 4:
            print("⚠️ Incomplete header received, connection may be unstable.")
            return None # Assume failure for simplicity

        message_len = struct.unpack('!I', header_data)[0]

        # Safety check for large messages
        if message_len > 10 * 1024 * 1024: # e.g., > 10MB
             print(f"❌ Declared message length too large: {message_len}. Aborting receive.")
             # Consider closing the socket or handling error state
             return None

        # Now read exactly message_len bytes
        message_data = b""
        bytes_to_read = message_len
        while len(message_data) < message_len:
            # Read in chunks
            chunk_size = min(4096, bytes_to_read)
            chunk = sock.recv(chunk_size)
            if not chunk:
                print("🔌 Connection closed by server while receiving message body.")
                return None # Connection lost
            message_data += chunk
            bytes_to_read -= len(chunk)

        # Decode and parse the JSON message
        try:
             return json.loads(message_data.decode('utf-8'))
        except json.JSONDecodeError as e:
             print(f"❌ JSON decode error: {e}. Data received (partial): {message_data[:100]}...")
             return None

    except socket.timeout:
        print("⏳ Socket timed out waiting for message.")
        return None
    except struct.error as e:
        print(f"❌ Error unpacking header: {e}")
        return None
    except socket.error as e:
        print(f"❌ Socket error receiving framed message: {e}")
        # This often indicates the connection is broken
        return None
    except Exception as e:
        print(f"❌ Unexpected error receiving framed message: {e}")
        return None

# You can add other client-specific helpers here if needed
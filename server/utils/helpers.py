#!/usr/bin/env python3
"""
Helper utilities for the LAN Communication Server
"""

import logging
import os
import sys
from datetime import datetime


# Add these imports at the top if not already present
import json
import struct
import socket # Keep existing imports like logging, os, sys, datetime

# ...(keep existing functions like setup_logging, log_event, etc.)...

# Helper to send a framed message (NEW)
def send_framed_message(sock, message_dict):
    """Sends a JSON message prefixed with its length."""
    try:
        message_json = json.dumps(message_dict).encode('utf-8')
        message_len = len(message_json)
        # Pack the length into 4 bytes (unsigned integer, network byte order)
        header = struct.pack('!I', message_len)
        sock.sendall(header + message_json) # Send header then message
        return True
    except socket.error as e:
        log_error(f"Socket error sending framed message: {e}")
        return False
    except Exception as e:
        log_error(f"Error sending framed message: {e}")
        return False

# Helper to receive a framed message (NEW)
def receive_framed_message(sock):
    """Receives a length-prefixed JSON message."""
    try:
        # Read the 4-byte header first
        header_data = sock.recv(4)
        if not header_data:
            log_event("Connection closed by client while receiving header.")
            return None
        if len(header_data) < 4:
            log_warning("Incomplete header received, connection may be unstable.")
            # In a production scenario, you might try to read more, but here we'll assume failure
            return None

        message_len = struct.unpack('!I', header_data)[0]

        # Check for unreasonably large messages (e.g., > 10MB) to prevent memory issues
        if message_len > 10 * 1024 * 1024:
             log_error(f"Declared message length too large: {message_len}. Closing connection.")
             # Consider closing the socket here
             return None

        # Now read exactly message_len bytes
        message_data = b""
        bytes_to_read = message_len
        while len(message_data) < message_len:
            # Read in chunks to avoid blocking for too long on massive messages
            chunk_size = min(4096, bytes_to_read)
            chunk = sock.recv(chunk_size)
            if not chunk:
                log_event("Connection closed by client while receiving message body.")
                return None # Connection lost before full message received
            message_data += chunk
            bytes_to_read -= len(chunk)

        # Decode and parse the JSON message
        try:
             return json.loads(message_data.decode('utf-8'))
        except json.JSONDecodeError as e:
             log_error(f"JSON decode error: {e}. Data received (partial): {message_data[:100]}...")
             return None

    except socket.timeout:
        # This can happen if the socket has a timeout, handle as needed
        log_warning("Socket timed out waiting for message.")
        return None
    except struct.error as e:
        log_error(f"Error unpacking header: {e}")
        return None
    except socket.error as e:
        log_error(f"Socket error receiving framed message: {e}")
        return None # Indicate connection issue
    except Exception as e:
        log_error(f"Unexpected error receiving framed message: {e}")
        return None


def setup_logging():
    """Setup logging configuration"""
    log_dir = "server/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"server_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def log_event(message):
    """Log an event"""
    logging.info(message)

def log_error(message):
    """Log an error"""
    logging.error(message)

def log_warning(message):
    """Log a warning"""
    logging.warning(message)

def get_timestamp():
    """Get current timestamp as string"""
    return datetime.now().isoformat()

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3:
        return False
    if len(username) > 20:
        return False
    if not username.replace('_', '').replace('-', '').isalnum():
        return False
    return True

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    # Remove or replace dangerous characters
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def create_safe_path(base_path, filename):
    """Create a safe file path"""
    safe_filename = sanitize_filename(filename)
    return os.path.join(base_path, safe_filename)

def get_local_ip():
    """Get local IP address"""
    import socket
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def calculate_bandwidth(bytes_transferred, time_elapsed):
    """Calculate bandwidth in bytes per second"""
    if time_elapsed <= 0:
        return 0
    return bytes_transferred / time_elapsed

def format_bandwidth(bps):
    """Format bandwidth in human readable format"""
    if bps < 1024:
        return f"{bps:.1f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps/1024:.1f} KB/s"
    elif bps < 1024 * 1024 * 1024:
        return f"{bps/(1024*1024):.1f} MB/s"
    else:
        return f"{bps/(1024*1024*1024):.1f} GB/s"

def is_port_available(host, port):
    """Check if a port is available"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False

def find_available_port(host, start_port, max_attempts=100):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(host, port):
            return port
    return None

def cleanup_old_files(directory, max_age_days=7):
    """Clean up old files from directory"""
    import time
    
    if not os.path.exists(directory):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    log_event(f"Cleaned up old file: {filename}")
                except Exception as e:
                    log_error(f"Error cleaning up {filename}: {e}")

def broadcast_message(server, message, exclude_username=None):
    """Broadcast message to all clients except specified one"""
    for username in server.clients:
        if username != exclude_username:
            server.send_to_client(username, message)

def get_system_info():
    """Get basic system information"""
    import platform
    
    info = {
        'platform': platform.system(),
        'platform_version': platform.version(),
        'architecture': platform.architecture()[0],
        'python_version': platform.python_version(),
        'cpu_count': 1,  # Default value
        'memory_total': 0,  # Default value
        'memory_available': 0  # Default value
    }
    
    try:
        import psutil
        info['cpu_count'] = psutil.cpu_count()
        info['memory_total'] = psutil.virtual_memory().total
        info['memory_available'] = psutil.virtual_memory().available
    except ImportError:
        pass  # psutil not available
    
    return info

#!/usr/bin/env python3
"""
File Module - Handles file upload and download using TCP
"""

import os
import threading
import time
import hashlib
from datetime import datetime

class FileModule:
    def __init__(self, server):
        self.server = server
        self.running = False
        self.file_thread = None
        self.upload_dir = "server/uploads"
        self.file_registry = {}  # {file_id: file_info}
        self.upload_sessions = {}  # {username: upload_info}
        
        # Create upload directory
        os.makedirs(self.upload_dir, exist_ok=True)
        
    def start(self):
        """Start the file module"""
        self.running = True
        self.file_thread = threading.Thread(target=self.file_loop, daemon=True)
        self.file_thread.start()
        print("📂 File module started")
    
    def stop(self):
        """Stop the file module"""
        self.running = False
        if self.file_thread:
            self.file_thread.join()
        print("📂 File module stopped")
    
    def file_loop(self):
        """Main file processing loop (placeholder for future features)"""
        while self.running:
            time.sleep(1)  # Simple loop for now
    
    def handle_upload(self, username, message_data, client_socket):
        """Handle file upload request"""
        if not self.running or username not in self.server.clients:
            return
        
        filename = message_data.get('filename', '')
        file_size = message_data.get('file_size', 0)
        file_hash = message_data.get('file_hash', '')
        
        if not filename or file_size <= 0:
            self.send_error(client_socket, "Invalid file information")
            return
        
        # Generate unique file ID
        file_id = self.generate_file_id(username, filename)
        
        # Create file info
        file_info = {
            'file_id': file_id,
            'filename': filename,
            'file_size': file_size,
            'file_hash': file_hash,
            'uploader': username,
            'upload_time': datetime.now().isoformat(),
            'file_path': os.path.join(self.upload_dir, file_id),
            'downloads': 0
        }
        
        # Register file
        self.file_registry[file_id] = file_info
        
        # Start upload session
        self.upload_sessions[username] = {
            'file_id': file_id,
            'file_path': file_info['file_path'],
            'bytes_received': 0,
            'file_size': file_size
        }
        
        # Send upload confirmation
        response = {
            'type': 'upload_confirmed',
            'file_id': file_id,
            'message': 'Ready to receive file data'
        }
        self.send_response(client_socket, response)
        
        print(f"📤 {username} uploading {filename} ({file_size} bytes)")
    
    def handle_download(self, username, message_data, client_socket):
        """Handle file download request"""
        if not self.running or username not in self.server.clients:
            return
        
        file_id = message_data.get('file_id', '')
        
        if file_id not in self.file_registry:
            self.send_error(client_socket, "File not found")
            return
        
        file_info = self.file_registry[file_id]
        file_path = file_info['file_path']
        
        if not os.path.exists(file_path):
            self.send_error(client_socket, "File no longer available")
            return
        
        # Update download count
        file_info['downloads'] += 1
        
        # Send file data
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Send file in chunks
            chunk_size = 4096
            total_chunks = (len(file_data) + chunk_size - 1) // chunk_size
            
            # Send file info first
            file_response = {
                'type': 'file_data_start',
                'filename': file_info['filename'],
                'file_size': len(file_data),
                'total_chunks': total_chunks
            }
            self.send_response(client_socket, file_response)
            
            # Send file chunks
            for i in range(0, len(file_data), chunk_size):
                chunk = file_data[i:i + chunk_size]
                chunk_response = {
                    'type': 'file_data_chunk',
                    'chunk_index': i // chunk_size,
                    'chunk_data': chunk.hex()  # Convert to hex string
                }
                self.send_response(client_socket, chunk_response)
            
            # Send completion
            completion_response = {
                'type': 'file_data_complete',
                'file_id': file_id
            }
            self.send_response(client_socket, completion_response)
            
            print(f"📥 {username} downloaded {file_info['filename']}")
            
        except Exception as e:
            self.send_error(client_socket, f"Error sending file: {e}")
    
    def handle_file_data(self, username, message_data, client_socket):
        """Handle incoming file data during upload"""
        if username not in self.upload_sessions:
            return
        
        upload_session = self.upload_sessions[username]
        file_path = upload_session['file_path']
        chunk_data = bytes.fromhex(message_data.get('chunk_data', ''))
        
        try:
            # Append chunk to file
            with open(file_path, 'ab') as f:
                f.write(chunk_data)
            
            upload_session['bytes_received'] += len(chunk_data)
            
            # Send progress update
            progress = (upload_session['bytes_received'] / upload_session['file_size']) * 100
            progress_response = {
                'type': 'upload_progress',
                'progress': progress,
                'bytes_received': upload_session['bytes_received'],
                'file_size': upload_session['file_size']
            }
            self.send_response(client_socket, progress_response)
            
            # Check if upload is complete
            if upload_session['bytes_received'] >= upload_session['file_size']:
                self.complete_upload(username)
                
        except Exception as e:
            self.send_error(client_socket, f"Error saving file: {e}")
    
    def complete_upload(self, username):
        """Complete file upload and notify all clients"""
        if username not in self.upload_sessions:
            return
        
        upload_session = self.upload_sessions[username]
        file_id = upload_session['file_id']
        
        if file_id in self.file_registry:
            file_info = self.file_registry[file_id]
            
            # Verify file hash
            if self.verify_file_hash(file_info['file_path'], file_info['file_hash']):
                # Notify all clients about new file
                notification = {
                    'type': 'file_available',
                    'file_info': {
                        'file_id': file_id,
                        'filename': file_info['filename'],
                        'file_size': file_info['file_size'],
                        'uploader': file_info['uploader'],
                        'upload_time': file_info['upload_time']
                    }
                }
                self.server.broadcast_to_all(notification)
                
                print(f"✅ {username} completed upload: {file_info['filename']}")
            else:
                print(f"❌ File hash verification failed for {username}")
                # Remove invalid file
                if os.path.exists(file_info['file_path']):
                    os.remove(file_info['file_path'])
                del self.file_registry[file_id]
        
        # Clean up upload session
        del self.upload_sessions[username]
    
    def generate_file_id(self, username, filename):
        """Generate unique file ID"""
        timestamp = str(int(time.time()))
        content = f"{username}_{filename}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def verify_file_hash(self, file_path, expected_hash):
        """Verify file integrity using hash"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            actual_hash = hashlib.md5(file_data).hexdigest()
            return actual_hash == expected_hash
        except Exception:
            return False
    
    def get_available_files(self):
        """Get list of available files"""
        return list(self.file_registry.values())
    
    def send_response(self, client_socket, response):
        """Send response to client"""
        try:
            import json
            data = json.dumps(response).encode('utf-8')
            client_socket.send(data)
        except Exception as e:
            print(f"❌ Error sending response: {e}")
    
    def send_error(self, client_socket, error_message):
        """Send error message to client"""
        error_response = {
            'type': 'error',
            'message': error_message
        }
        self.send_response(client_socket, error_response)

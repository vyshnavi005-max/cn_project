#!/usr/bin/env python3
"""
File Client - Handles file upload and download
"""

import os
import hashlib
import threading
import time
from datetime import datetime

class FileClient:
    def __init__(self, main_client):
        self.main_client = main_client
        self.available_files = {}  # {file_id: file_info}
        self.upload_progress = {}  # {file_id: progress_info}
        self.download_progress = {}  # {file_id: progress_info}
        self.download_dir = "client/downloads"
        
        # Create download directory
        os.makedirs(self.download_dir, exist_ok=True)
        
    def upload_file(self, file_path):
        """Upload file to server"""
        if not self.main_client.connected:
            print("❌ Not connected to server")
            return False
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
        
        try:
            # Get file information
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Calculate file hash
            file_hash = self.calculate_file_hash(file_path)
            
            # Send upload request to server
            self.main_client.send_file_upload(filename, file_size, file_hash)
            
            print(f"📤 Uploading {filename} ({self.format_file_size(file_size)})")
            return True
            
        except Exception as e:
            print(f"❌ Error uploading file: {e}")
            return False
    
    def download_file(self, file_id):
        """Download file from server"""
        if not self.main_client.connected:
            print("❌ Not connected to server")
            return False
        
        if file_id not in self.available_files:
            print(f"❌ File not available: {file_id}")
            return False
        
        try:
            # Send download request to server
            self.main_client.send_file_download(file_id)
            
            file_info = self.available_files[file_id]
            print(f"📥 Downloading {file_info['filename']}")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading file: {e}")
            return False
    
    def handle_file_available(self, file_info):
        """Handle file availability notification from server"""
        try:
            file_id = file_info['file_id']
            self.available_files[file_id] = file_info
            
            # Update GUI if available
            if self.main_client.main_window:
                self.main_client.main_window.update_file_list()
            
            print(f"📂 New file available: {file_info['filename']} by {file_info['uploader']}")
            
        except Exception as e:
            print(f"❌ Error handling file availability: {e}")
    
    def handle_file_data_start(self, message_data):
        """Handle start of file data transfer"""
        try:
            filename = message_data['filename']
            file_size = message_data['file_size']
            total_chunks = message_data['total_chunks']
            
            # Initialize download progress
            file_id = f"download_{int(time.time())}"
            self.download_progress[file_id] = {
                'filename': filename,
                'file_size': file_size,
                'total_chunks': total_chunks,
                'received_chunks': 0,
                'file_data': b'',
                'start_time': time.time()
            }
            
            print(f"📥 Starting download: {filename} ({self.format_file_size(file_size)})")
            
        except Exception as e:
            print(f"❌ Error handling file data start: {e}")
    
    def handle_file_data_chunk(self, message_data):
        """Handle file data chunk"""
        try:
            chunk_index = message_data['chunk_index']
            chunk_data = bytes.fromhex(message_data['chunk_data'])
            
            # Find the download session (simplified - in practice you'd track this better)
            for file_id, progress in self.download_progress.items():
                if progress['received_chunks'] == chunk_index:
                    progress['file_data'] += chunk_data
                    progress['received_chunks'] += 1
                    
                    # Calculate progress percentage
                    progress_percent = (progress['received_chunks'] / progress['total_chunks']) * 100
                    
                    print(f"📥 Download progress: {progress_percent:.1f}%")
                    
                    # Update GUI if available
                    if self.main_client.main_window:
                        self.main_client.main_window.update_download_progress(file_id, progress_percent)
                    
                    break
                    
        except Exception as e:
            print(f"❌ Error handling file data chunk: {e}")
    
    def handle_file_data_complete(self, message_data):
        """Handle completion of file data transfer"""
        try:
            file_id = message_data['file_id']
            
            # Find the download session
            for download_id, progress in self.download_progress.items():
                if progress['received_chunks'] == progress['total_chunks']:
                    # Save file
                    file_path = os.path.join(self.download_dir, progress['filename'])
                    
                    with open(file_path, 'wb') as f:
                        f.write(progress['file_data'])
                    
                    # Calculate transfer time and speed
                    transfer_time = time.time() - progress['start_time']
                    speed = progress['file_size'] / transfer_time if transfer_time > 0 else 0
                    
                    print(f"✅ Download complete: {progress['filename']}")
                    print(f"   Size: {self.format_file_size(progress['file_size'])}")
                    print(f"   Time: {transfer_time:.1f}s")
                    print(f"   Speed: {self.format_bandwidth(speed)}")
                    
                    # Clean up progress tracking
                    del self.download_progress[download_id]
                    
                    # Update GUI if available
                    if self.main_client.main_window:
                        self.main_client.main_window.update_file_list()
                    
                    break
                    
        except Exception as e:
            print(f"❌ Error handling file data complete: {e}")
    
    def calculate_file_hash(self, file_path):
        """Calculate MD5 hash of file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"❌ Error calculating file hash: {e}")
            return ""
    
    def verify_file_integrity(self, file_path, expected_hash):
        """Verify file integrity using hash"""
        actual_hash = self.calculate_file_hash(file_path)
        return actual_hash == expected_hash
    
    def get_available_files(self):
        """Get list of available files"""
        return list(self.available_files.values())
    
    def get_upload_progress(self):
        """Get upload progress information"""
        return self.upload_progress.copy()
    
    def get_download_progress(self):
        """Get download progress information"""
        return self.download_progress.copy()
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def format_bandwidth(self, bps):
        """Format bandwidth in human readable format"""
        if bps < 1024:
            return f"{bps:.1f} B/s"
        elif bps < 1024 * 1024:
            return f"{bps/1024:.1f} KB/s"
        elif bps < 1024 * 1024 * 1024:
            return f"{bps/(1024*1024):.1f} MB/s"
        else:
            return f"{bps/(1024*1024*1024):.1f} GB/s"
    
    def cleanup_old_files(self, max_age_days=30):
        """Clean up old downloaded files"""
        if not os.path.exists(self.download_dir):
            return
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for filename in os.listdir(self.download_dir):
            file_path = os.path.join(self.download_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Cleaned up old file: {filename}")
                    except Exception as e:
                        print(f"❌ Error cleaning up {filename}: {e}")
    
    def get_download_directory(self):
        """Get download directory path"""
        return self.download_dir
    
    def set_download_directory(self, directory):
        """Set download directory"""
        try:
            os.makedirs(directory, exist_ok=True)
            self.download_dir = directory
            print(f"📁 Download directory set to: {directory}")
            return True
        except Exception as e:
            print(f"❌ Error setting download directory: {e}")
            return False

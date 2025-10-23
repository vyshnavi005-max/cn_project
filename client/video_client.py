#!/usr/bin/env python3
"""
Video Client - Handles video capture, compression, and display
"""

import cv2
import numpy as np
import threading
import time
import struct
from datetime import datetime

class VideoClient:
    def __init__(self, main_client):
        self.main_client = main_client
        self.camera = None
        self.capturing = False
        self.displaying = False
        self.video_thread = None
        self.display_thread = None
        self.received_frames = {}  # {username: frame_data}
        self.frame_lock = threading.Lock()
        
        # Video settings
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 15
        self.quality = 50
        
    def start_camera(self):
        """Start video capture from camera"""
        try:
            # Try different camera backends
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                try:
                    self.camera = cv2.VideoCapture(0, backend)
                    if self.camera.isOpened():
                        # Test if we can actually read a frame
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            print(f"📹 Camera started with backend {backend}")
                            break
                        else:
                            self.camera.release()
                            self.camera = None
                except Exception:
                    continue
            
            if not self.camera or not self.camera.isOpened():
                print("❌ Could not open camera with any backend")
                return False
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            self.capturing = True
            self.video_thread = threading.Thread(target=self.capture_loop, daemon=True)
            self.video_thread.start()
            
            print("📹 Camera started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error starting camera: {e}")
            return False
    
    def stop_camera(self):
        """Stop video capture"""
        self.capturing = False
        if self.camera:
            self.camera.release()
            self.camera = None
        print("📹 Camera stopped")
    
    def capture_loop(self):
        """Main video capture loop"""
        consecutive_failures = 0
        max_failures = 10
        
        while self.capturing and self.camera:
            try:
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Store frame for local display
                    with self.frame_lock:
                        self.received_frames[self.main_client.username] = {
                            'frame': frame.copy(),
                            'timestamp': time.time()
                        }
                    
                    # Compress frame
                    compressed_frame = self.compress_frame(frame)
                    if compressed_frame:
                        # Debug: Print every 30 frames (once per 2 seconds at 15fps)
                        if hasattr(self, 'frame_count'):
                            self.frame_count += 1
                        else:
                            self.frame_count = 1
                        
                        if self.frame_count % 30 == 0:
                            print(f"📹 Compressed frame {self.frame_count} ({len(compressed_frame)} bytes)")
                        
                        # Send to server
                        print(f"📹 DEBUG: About to send video frame {self.frame_count}")
                        self.main_client.send_video_frame(compressed_frame)
                    else:
                        print("❌ Failed to compress video frame")
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print(f"❌ Too many consecutive camera failures ({consecutive_failures}), stopping camera")
                        break
                    time.sleep(0.1)  # Short delay before retry
                
                # Control frame rate
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"❌ Error in capture loop: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
                time.sleep(0.1)
    
    def compress_frame(self, frame):
        """Compress video frame using JPEG"""
        try:
            # Resize frame if needed
            if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            
            if result:
                return encoded_img.tobytes()
            return None
        except Exception as e:
            print(f"❌ Error compressing frame: {e}")
            return None
    
    def decompress_frame(self, frame_data):
        """Decompress video frame from JPEG"""
        try:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"❌ Error decompressing frame: {e}")
            return None
    
    def handle_received_frame(self, username, frame_data):
        """Handle received video frame from server"""
        try:
            # Decompress frame
            frame = self.decompress_frame(frame_data)
            if frame is not None:
                with self.frame_lock:
                    self.received_frames[username] = {
                        'frame': frame,
                        'timestamp': time.time()
                    }
                
                # Debug: Print when receiving frames
                if hasattr(self, 'receive_count'):
                    self.receive_count += 1
                else:
                    self.receive_count = 1
                
                if self.receive_count % 30 == 0:
                    print(f"📹 Received video frame {self.receive_count} from {username}")
                
                # Update display if GUI is available
                if self.main_client.main_window:
                    self.main_client.main_window.update_video_display()
        except Exception as e:
            print(f"❌ Error handling received frame: {e}")
    
    def get_received_frames(self):
        """Get all received frames"""
        with self.frame_lock:
            return self.received_frames.copy()
    
    def clear_old_frames(self, max_age=5.0):
        """Clear old frames from buffer"""
        current_time = time.time()
        with self.frame_lock:
            to_remove = []
            for username, frame_data in self.received_frames.items():
                if current_time - frame_data['timestamp'] > max_age:
                    to_remove.append(username)
            
            for username in to_remove:
                del self.received_frames[username]
    
    def start_display(self):
        """Start video display (for testing without GUI)"""
        self.displaying = True
        self.display_thread = threading.Thread(target=self.display_loop, daemon=True)
        self.display_thread.start()
    
    def stop_display(self):
        """Stop video display"""
        self.displaying = False
        cv2.destroyAllWindows()
    
    def display_loop(self):
        """Display loop for testing"""
        while self.displaying:
            try:
                frames = self.get_received_frames()
                if frames:
                    # Create grid display
                    self.create_grid_display(frames)
                
                time.sleep(1.0 / 30)  # 30 FPS display
                
            except Exception as e:
                print(f"❌ Error in display loop: {e}")
                break
    
    def create_grid_display(self, frames):
        """Create grid display of all video frames"""
        try:
            if not frames:
                return
            
            # Calculate grid dimensions
            num_frames = len(frames)
            cols = int(np.ceil(np.sqrt(num_frames)))
            rows = int(np.ceil(num_frames / cols))
            
            # Create grid
            grid_height = rows * self.frame_height
            grid_width = cols * self.frame_width
            grid = np.zeros((grid_height, grid_width, 3), dtype=np.uint8)
            
            # Place frames in grid
            for i, (username, frame_data) in enumerate(frames.items()):
                frame = frame_data['frame']
                row = i // cols
                col = i % cols
                
                y_start = row * self.frame_height
                y_end = y_start + self.frame_height
                x_start = col * self.frame_width
                x_end = x_start + self.frame_width
                
                # Resize frame to fit grid cell
                resized_frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                grid[y_start:y_end, x_start:x_end] = resized_frame
                
                # Add username label
                cv2.putText(grid, username, (x_start + 10, y_start + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display grid
            cv2.imshow('Video Conference', grid)
            cv2.waitKey(1)
            
        except Exception as e:
            print(f"❌ Error creating grid display: {e}")
    
    def set_quality(self, quality):
        """Set video quality (1-100)"""
        self.quality = max(1, min(100, quality))
        print(f"📹 Video quality set to {self.quality}")
    
    def set_resolution(self, width, height):
        """Set video resolution"""
        self.frame_width = width
        self.frame_height = height
        print(f"📹 Video resolution set to {width}x{height}")
    
    def get_camera_info(self):
        """Get camera information"""
        if self.camera and self.camera.isOpened():
            return {
                'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': self.camera.get(cv2.CAP_PROP_FPS),
                'is_opened': True
            }
        return {'is_opened': False}

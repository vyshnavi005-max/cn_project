#!/usr/bin/env python3
"""
Screen Share Client - Handles screen/slide sharing
"""

import threading
import time
import base64
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageGrab
import io

class ScreenShareClient:
    def __init__(self, main_client):
        self.main_client = main_client
        self.sharing = False
        self.viewing = False
        self.share_thread = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Screen capture settings
        self.capture_fps = 10  # Lower FPS for screen sharing
        self.quality = 70
        self.max_width = 1920
        self.max_height = 1080
        
    def start_sharing(self):
        """Start screen sharing"""
        if not self.main_client.connected:
            print("❌ Not connected to server")
            return False
        
        if self.sharing:
            print("❌ Already sharing screen")
            return False
        
        try:
            self.sharing = True
            self.share_thread = threading.Thread(target=self.capture_loop, daemon=True)
            self.share_thread.start()
            
            # Notify server
            self.main_client.start_screen_sharing()
            
            print("🖼️ Screen sharing started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting screen sharing: {e}")
            self.sharing = False
            return False
    
    def stop_sharing(self):
        """Stop screen sharing"""
        if not self.sharing:
            return
        
        self.sharing = False
        
        # Notify server
        self.main_client.stop_screen_sharing()
        
        print("🖼️ Screen sharing stopped")
    
    def capture_loop(self):
        """Main screen capture loop"""
        while self.sharing:
            try:
                # Capture screen
                screenshot = ImageGrab.grab()
                
                # Convert to OpenCV format
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Resize if needed
                frame = self.resize_frame(frame)
                
                # Compress frame
                compressed_frame = self.compress_frame(frame)
                
                if compressed_frame:
                    # Send to server
                    self.send_frame_to_server(compressed_frame)
                
                # Control frame rate
                time.sleep(1.0 / self.capture_fps)
                
            except Exception as e:
                print(f"❌ Error in screen capture: {e}")
                break
    
    def resize_frame(self, frame):
        """Resize frame to fit within max dimensions"""
        try:
            height, width = frame.shape[:2]
            
            # Calculate new dimensions while maintaining aspect ratio
            if width > self.max_width or height > self.max_height:
                ratio = min(self.max_width / width, self.max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            return frame
        except Exception as e:
            print(f"❌ Error resizing frame: {e}")
            return frame
    
    def compress_frame(self, frame):
        """Compress screen frame using JPEG"""
        try:
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
        """Decompress screen frame from JPEG"""
        try:
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"❌ Error decompressing frame: {e}")
            return None
    
    def send_frame_to_server(self, frame_data):
        """Send frame data to server"""
        try:
            # Encode frame data as base64 for transmission
            encoded_data = base64.b64encode(frame_data).decode('utf-8')
            
            frame_message = {
                'type': 'screen_frame',
                'frame_data': encoded_data,
                'format': 'jpeg',
                'timestamp': time.time()
            }
            
            self.main_client.send_tcp_message(frame_message)
            
        except Exception as e:
            print(f"❌ Error sending frame to server: {e}")
    
    def handle_presentation_started(self, message_data):
        """Handle presentation started notification"""
        try:
            presenter = message_data.get('presenter', 'Unknown')
            timestamp = message_data.get('timestamp', '')
            
            self.viewing = True
            
            # Update GUI if available
            if self.main_client.main_window:
                self.main_client.main_window.update_screen_share_display()
            
            print(f"🖼️ {presenter} started screen sharing")
            
        except Exception as e:
            print(f"❌ Error handling presentation started: {e}")
    
    def handle_presentation_stopped(self, message_data):
        """Handle presentation stopped notification"""
        try:
            presenter = message_data.get('presenter', 'Unknown')
            
            self.viewing = False
            
            # Clear current frame
            with self.frame_lock:
                self.current_frame = None
            
            # Update GUI if available
            if self.main_client.main_window:
                self.main_client.main_window.update_screen_share_display()
            
            print(f"🖼️ {presenter} stopped screen sharing")
            
        except Exception as e:
            print(f"❌ Error handling presentation stopped: {e}")
    
    def handle_screen_frame(self, message_data):
        """Handle incoming screen frame from server"""
        try:
            frame_data = message_data.get('frame_data', '')
            presenter = message_data.get('presenter', 'Unknown')
            timestamp = message_data.get('timestamp', time.time())
            
            if not frame_data:
                return
            
            # Decode base64 data
            try:
                decoded_data = base64.b64decode(frame_data)
            except Exception:
                return
            
            # Decompress frame
            frame = self.decompress_frame(decoded_data)
            
            if frame is not None:
                # Store current frame
                with self.frame_lock:
                    self.current_frame = {
                        'frame': frame,
                        'presenter': presenter,
                        'timestamp': timestamp
                    }
                
                # Update GUI if available
                if self.main_client.main_window:
                    self.main_client.main_window.update_screen_share_display()
            
        except Exception as e:
            print(f"❌ Error handling screen frame: {e}")
    
    def get_current_frame(self):
        """Get current screen frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame else None
    
    def is_sharing(self):
        """Check if currently sharing screen"""
        return self.sharing
    
    def is_viewing(self):
        """Check if currently viewing shared screen"""
        return self.viewing
    
    def set_quality(self, quality):
        """Set screen share quality (1-100)"""
        self.quality = max(1, min(100, quality))
        print(f"🖼️ Screen share quality set to {self.quality}")
    
    def set_fps(self, fps):
        """Set screen capture FPS"""
        self.capture_fps = max(1, min(30, fps))
        print(f"🖼️ Screen capture FPS set to {self.capture_fps}")
    
    def set_resolution(self, max_width, max_height):
        """Set maximum screen resolution"""
        self.max_width = max_width
        self.max_height = max_height
        print(f"🖼️ Max screen resolution set to {max_width}x{max_height}")
    
    def capture_application_window(self, window_title):
        """Capture specific application window (Windows only)"""
        try:
            import win32gui
            import win32ui
            import win32con
            
            # Find window by title
            hwnd = win32gui.FindWindow(None, window_title)
            if not hwnd:
                print(f"❌ Window not found: {window_title}")
                return None
            
            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Capture window
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            # Convert to PIL Image
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return img
            
        except ImportError:
            print("❌ win32gui not available for window capture")
            return None
        except Exception as e:
            print(f"❌ Error capturing window: {e}")
            return None

#!/usr/bin/env python3
"""
Compression utilities for video, audio, and file data
"""

import zlib
import gzip
import base64
import cv2
import numpy as np
from PIL import Image
import io

class CompressionUtils:
    """Utility class for various compression methods"""
    
    @staticmethod
    def compress_video_frame(frame, quality=50):
        """Compress video frame using JPEG compression"""
        try:
            # Convert BGR to RGB if needed
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                frame_rgb = frame
            
            # Encode as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            result, encoded_img = cv2.imencode('.jpg', frame_rgb, encode_param)
            
            if result:
                return encoded_img.tobytes()
            return None
        except Exception as e:
            print(f"❌ Error compressing video frame: {e}")
            return None
    
    @staticmethod
    def decompress_video_frame(compressed_data):
        """Decompress video frame from JPEG"""
        try:
            nparr = np.frombuffer(compressed_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"❌ Error decompressing video frame: {e}")
            return None
    
    @staticmethod
    def compress_screen_frame(frame_data, quality=70):
        """Compress screen frame using PIL and JPEG"""
        try:
            # If frame_data is already bytes, convert to PIL Image
            if isinstance(frame_data, bytes):
                image = Image.open(io.BytesIO(frame_data))
            else:
                image = frame_data
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Compress using JPEG
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            return output.getvalue()
        except Exception as e:
            print(f"❌ Error compressing screen frame: {e}")
            return None
    
    @staticmethod
    def decompress_screen_frame(compressed_data):
        """Decompress screen frame from JPEG"""
        try:
            image = Image.open(io.BytesIO(compressed_data))
            return image
        except Exception as e:
            print(f"❌ Error decompressing screen frame: {e}")
            return None
    
    @staticmethod
    def compress_audio_data(audio_data, compression_level=6):
        """Compress audio data using zlib"""
        try:
            return zlib.compress(audio_data, compression_level)
        except Exception as e:
            print(f"❌ Error compressing audio data: {e}")
            return None
    
    @staticmethod
    def decompress_audio_data(compressed_data):
        """Decompress audio data using zlib"""
        try:
            return zlib.decompress(compressed_data)
        except Exception as e:
            print(f"❌ Error decompressing audio data: {e}")
            return None
    
    @staticmethod
    def compress_file_data(file_data, compression_level=6):
        """Compress file data using gzip"""
        try:
            return gzip.compress(file_data, compression_level)
        except Exception as e:
            print(f"❌ Error compressing file data: {e}")
            return None
    
    @staticmethod
    def decompress_file_data(compressed_data):
        """Decompress file data using gzip"""
        try:
            return gzip.decompress(compressed_data)
        except Exception as e:
            print(f"❌ Error decompressing file data: {e}")
            return None
    
    @staticmethod
    def encode_base64(data):
        """Encode data as base64 string"""
        try:
            return base64.b64encode(data).decode('utf-8')
        except Exception as e:
            print(f"❌ Error encoding base64: {e}")
            return None
    
    @staticmethod
    def decode_base64(encoded_data):
        """Decode base64 string to data"""
        try:
            return base64.b64decode(encoded_data)
        except Exception as e:
            print(f"❌ Error decoding base64: {e}")
            return None
    
    @staticmethod
    def calculate_compression_ratio(original_size, compressed_size):
        """Calculate compression ratio"""
        if original_size == 0:
            return 0
        return (1 - compressed_size / original_size) * 100
    
    @staticmethod
    def optimize_for_bandwidth(data, target_size):
        """Optimize data size for bandwidth constraints"""
        if len(data) <= target_size:
            return data
        
        # For images, reduce quality
        if isinstance(data, bytes) and data.startswith(b'\xff\xd8'):  # JPEG header
            try:
                # This is a simplified approach - in practice you'd need more sophisticated resizing
                return data[:target_size]
            except:
                return data
        
        # For other data, truncate (not ideal but simple)
        return data[:target_size]
    
    @staticmethod
    def resize_image(image, max_width=1920, max_height=1080):
        """Resize image while maintaining aspect ratio"""
        try:
            if isinstance(image, np.ndarray):
                height, width = image.shape[:2]
            else:
                width, height = image.size
            
            # Calculate new dimensions
            ratio = min(max_width / width, max_height / height)
            if ratio >= 1:
                return image  # No need to resize
            
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            if isinstance(image, np.ndarray):
                return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            else:
                return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"❌ Error resizing image: {e}")
            return image

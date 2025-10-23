#!/usr/bin/env python3
"""
Audio Client - Handles audio capture and playback
"""

import pyaudio
import numpy as np
import threading
import time
import struct
import queue

class AudioClient:
    def __init__(self, main_client):
        self.main_client = main_client
        self.audio = None
        self.input_stream = None
        self.output_stream = None
        self.capturing = False
        self.playing = False
        self.audio_thread = None
        self.playback_thread = None
        
        # Audio settings
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.channels = 1
        self.format = pyaudio.paInt16
        
        # Audio buffers
        self.playback_queue = queue.Queue(maxsize=10)
        
        # Initialize PyAudio
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            print(f"❌ Error initializing PyAudio: {e}")
            self.audio = None
    
    def start_audio(self):
        """Start audio capture and playback"""
        if not self.audio:
            print("❌ PyAudio not available")
            return False
        
        try:
            # Start input stream (microphone)
            self.input_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            # Start output stream (speakers)
            self.output_stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.capturing = True
            self.playing = True
            
            # Start threads
            self.audio_thread = threading.Thread(target=self.capture_loop, daemon=True)
            self.playback_thread = threading.Thread(target=self.playback_loop, daemon=True)
            
            self.audio_thread.start()
            self.playback_thread.start()
            
            print("🎵 Audio started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting audio: {e}")
            return False
    
    def stop_audio(self):
        """Stop audio capture and playback"""
        self.capturing = False
        self.playing = False
        
        # Close streams
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None
        
        print("🎵 Audio stopped")
    
    def capture_loop(self):
        """Main audio capture loop"""
        while self.capturing and self.input_stream:
            try:
                # Read audio data from microphone
                audio_data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Convert to numpy array for processing
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Apply simple noise reduction (optional)
                audio_array = self.apply_noise_reduction(audio_array)
                
                # Send to server
                self.main_client.send_audio_data(audio_array.tobytes())
                
            except Exception as e:
                print(f"❌ Error in audio capture: {e}")
                break
    
    def playback_loop(self):
        """Main audio playback loop"""
        while self.playing and self.output_stream:
            try:
                # Get audio data from queue
                if not self.playback_queue.empty():
                    audio_data = self.playback_queue.get(timeout=0.1)
                    self.output_stream.write(audio_data)
                else:
                    time.sleep(0.01)  # Small delay if no data
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error in audio playback: {e}")
                break
    
    def handle_mixed_audio(self, audio_data, usernames):
        """Handle mixed audio from server"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Apply volume normalization
            audio_array = self.normalize_audio(audio_array)
            
            # Add to playback queue
            if not self.playback_queue.full():
                self.playback_queue.put(audio_array.tobytes())
                
        except Exception as e:
            print(f"❌ Error handling mixed audio: {e}")
    
    def apply_noise_reduction(self, audio_array):
        """Apply simple noise reduction"""
        try:
            # Simple high-pass filter to remove low-frequency noise
            # This is a basic implementation - more sophisticated methods can be used
            if len(audio_array) > 1:
                # Simple difference filter
                filtered = np.diff(audio_array, prepend=audio_array[0])
                return filtered.astype(np.int16)
            return audio_array
        except Exception:
            return audio_array
    
    def normalize_audio(self, audio_array):
        """Normalize audio volume"""
        try:
            # Calculate RMS (Root Mean Square) for volume normalization
            rms = np.sqrt(np.mean(audio_array**2))
            if rms > 0:
                # Normalize to prevent clipping
                max_val = 32767  # Maximum value for 16-bit audio
                normalized = audio_array * (max_val * 0.8) / rms
                return np.clip(normalized, -max_val, max_val).astype(np.int16)
            return audio_array
        except Exception:
            return audio_array
    
    def set_volume(self, volume):
        """Set audio volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        print(f"🎵 Volume set to {self.volume}")
    
    def mute_microphone(self):
        """Mute microphone"""
        self.capturing = False
        print("🎵 Microphone muted")
    
    def unmute_microphone(self):
        """Unmute microphone"""
        if self.audio and not self.capturing:
            self.capturing = True
            print("🎵 Microphone unmuted")
    
    def mute_speakers(self):
        """Mute speakers"""
        self.playing = False
        print("🎵 Speakers muted")
    
    def unmute_speakers(self):
        """Unmute speakers"""
        if self.audio and not self.playing:
            self.playing = True
            print("🎵 Speakers unmuted")
    
    def get_audio_devices(self):
        """Get list of available audio devices"""
        if not self.audio:
            return []
        
        devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': info['defaultSampleRate']
            })
        return devices
    
    def set_audio_device(self, device_index):
        """Set audio input device"""
        if not self.audio:
            return False
        
        try:
            # Stop current streams
            self.stop_audio()
            
            # Start with new device
            return self.start_audio()
        except Exception as e:
            print(f"❌ Error setting audio device: {e}")
            return False
    
    def get_audio_level(self):
        """Get current audio input level"""
        if not self.capturing or not self.input_stream:
            return 0.0
        
        try:
            # Read a small chunk to get current level
            audio_data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_array**2))
            return min(1.0, rms / 32767.0)  # Normalize to 0-1
        except Exception:
            return 0.0
    
    def cleanup(self):
        """Cleanup audio resources"""
        self.stop_audio()
        if self.audio:
            self.audio.terminate()
            self.audio = None

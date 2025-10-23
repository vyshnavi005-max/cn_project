# LAN Communication Application - Project Structure

## 📁 Complete Project Structure

```
LAN_Communication_App/
│
├── 📁 server/                          # Server-side modules
│   ├── main_server.py                  # 🎯 Main server controller
│   ├── video_module.py                 # 📹 Video streaming (UDP)
│   ├── audio_module.py                 # 🎵 Audio mixing (UDP)
│   ├── chat_module.py                  # 💬 Text messaging (TCP)
│   ├── file_module.py                  # 📂 File sharing (TCP)
│   ├── screen_share_module.py          # 🖼️ Screen sharing (TCP)
│   └── 📁 utils/                       # Utility modules
│       ├── helpers.py                  # 🔧 General utilities
│       └── compression.py              # 🗜️ Compression utilities
│
├── 📁 client/                          # Client-side modules
│   ├── main_client.py                  # 🎯 Main client controller
│   ├── video_client.py                 # 📹 Video capture/display
│   ├── audio_client.py                 # 🎵 Audio capture/playback
│   ├── chat_client.py                  # 💬 Chat interface
│   ├── file_client.py                  # 📂 File management
│   ├── screen_share_client.py          # 🖼️ Screen sharing
│   └── 📁 ui/                          # User interface
│       └── main_window.py              # 🖥️ GUI interface
│
├── 📁 server/uploads/                  # Server file storage
├── 📁 server/logs/                     # Server log files
├── 📁 client/downloads/                # Client download directory
│
├── 📄 requirements.txt                 # Python dependencies
├── 📄 README.md                        # Main documentation
├── 📄 PROJECT_STRUCTURE.md             # This file
├── 📄 start_server.py                  # Server startup script
├── 📄 start_client.py                  # Client startup script
└── 📄 test_connection.py               # Connection test script
```

## 🏗️ Architecture Overview

### Server Architecture
The server follows a modular design where each communication type is handled by a dedicated module:

- **main_server.py**: Central coordinator managing all connections and delegating tasks
- **video_module.py**: Handles UDP video streaming and broadcasting
- **audio_module.py**: Manages UDP audio capture, mixing, and distribution
- **chat_module.py**: Processes TCP text messages and maintains chat history
- **file_module.py**: Handles TCP file uploads/downloads with progress tracking
- **screen_share_module.py**: Manages TCP screen sharing with presenter controls

### Client Architecture
The client provides a unified interface integrating all communication features:

- **main_client.py**: Central controller managing server connection and module coordination
- **video_client.py**: Webcam capture, compression, and multi-user video display
- **audio_client.py**: Microphone capture, audio processing, and speaker output
- **chat_client.py**: Text messaging interface with user management
- **file_client.py**: File upload/download with progress tracking
- **screen_share_client.py**: Screen capture and shared screen viewing
- **ui/main_window.py**: Comprehensive GUI integrating all features

## 🔌 Communication Protocols

### TCP (Reliable Communication)
- **Port**: Server port (default: 5000)
- **Used for**: Chat messages, file transfers, screen sharing, control commands
- **Benefits**: Guaranteed delivery, error checking, ordered packets

### UDP (Low-Latency Streaming)
- **Video Port**: Server port + 1 (default: 5001)
- **Audio Port**: Server port + 2 (default: 5002)
- **Used for**: Video frames, audio streams
- **Benefits**: Low latency, real-time performance

## 📊 Data Flow

### Video Conferencing Flow
```
Client Camera → video_client.py → UDP → video_module.py → UDP → All Other Clients
```

### Audio Communication Flow
```
Client Mic → audio_client.py → UDP → audio_module.py → Mix → UDP → All Clients
```

### Chat Message Flow
```
Client Input → chat_client.py → TCP → chat_module.py → TCP → All Clients
```

### File Sharing Flow
```
Client File → file_client.py → TCP → file_module.py → Storage → Notification → All Clients
```

### Screen Sharing Flow
```
Client Screen → screen_share_client.py → TCP → screen_share_module.py → TCP → All Clients
```

## 🚀 Quick Start Guide

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p server/uploads server/logs client/downloads
```

### 2. Start Server
```bash
# Option 1: Direct execution
python server/main_server.py

# Option 2: Using startup script
python start_server.py
```

### 3. Start Clients
```bash
# On each client machine
python client/main_client.py

# Or using startup script
python start_client.py
```

### 4. Test Connection
```bash
python test_connection.py
```

## 🔧 Configuration Points

### Server Configuration
- **main_server.py**: Port settings, connection limits
- **file_module.py**: Upload directory, file size limits
- **utils/helpers.py**: Logging configuration

### Client Configuration
- **video_client.py**: Resolution, quality, frame rate
- **audio_client.py**: Sample rate, chunk size, device selection
- **file_client.py**: Download directory, progress tracking
- **screen_share_client.py**: Capture quality, FPS, resolution

## 🛠️ Development Notes

### Adding New Features
1. Create module in appropriate directory (server/ or client/)
2. Import and initialize in main controller
3. Add GUI elements in main_window.py
4. Update communication protocols if needed

### Debugging
- Enable debug logging in utils/helpers.py
- Use test_connection.py for network testing
- Check individual module logs

### Performance Optimization
- Adjust video quality based on network capacity
- Modify frame rates for different use cases
- Tune buffer sizes for audio/video
- Optimize compression settings

## 📋 Dependencies

### Core Requirements
- **opencv-python**: Video capture and processing
- **Pillow**: Image manipulation
- **numpy**: Numerical operations
- **pyaudio**: Audio capture and playback
- **pyautogui**: Screen capture
- **mss**: Cross-platform screen capture
- **psutil**: System information

### Optional Dependencies
- **PyQt5**: Advanced GUI features
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Code linting

## 🔒 Security Considerations

- **LAN-Only Design**: No internet connectivity required
- **No Encryption**: Designed for trusted LAN environments
- **Basic Validation**: File type and size validation
- **User Management**: Simple username-based identification

## 📈 Scalability

### Current Limitations
- Single server instance
- No load balancing
- Limited to LAN bandwidth
- Basic error handling

### Future Enhancements
- Multi-server support
- Load balancing
- Advanced compression
- Mobile client support
- Cloud integration options

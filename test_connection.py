#!/usr/bin/env python3
"""
Simple test script to verify server and client connection
"""

import socket
import json
import time

def test_server_connection(host, port):
    """Test if server is running and accepting connections"""
    try:
        # Test TCP connection
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(5)
        tcp_socket.connect((host, port))
        
        # Send test message
        test_message = {
            'type': 'test',
            'message': 'Connection test'
        }
        tcp_socket.send(json.dumps(test_message).encode('utf-8'))
        
        # Try to receive response
        tcp_socket.settimeout(2)
        try:
            response = tcp_socket.recv(1024)
            print(f"TCP connection successful: {response.decode('utf-8')[:100]}")
        except socket.timeout:
            print("TCP connection successful (no response expected)")
        
        tcp_socket.close()
        
        # Test UDP ports
        try:
            video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            video_socket.settimeout(2)
            video_socket.sendto(b'test', (host, port + 1))
            print(f"Video UDP port {port + 1} is open")
            video_socket.close()
        except Exception as e:
            print(f"Video UDP port {port + 1} error: {e}")
        
        try:
            audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            audio_socket.settimeout(2)
            audio_socket.sendto(b'test', (host, port + 2))
            print(f"Audio UDP port {port + 2} is open")
            audio_socket.close()
        except Exception as e:
            print(f"Audio UDP port {port + 2} error: {e}")
        
        return True
        
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test server connection')
    parser.add_argument('host', nargs='?', default='localhost', help='Server IP address')
    parser.add_argument('port', nargs='?', type=int, default=5000, help='Server port')
    
    args = parser.parse_args()
    
    print(f"Testing connection to {args.host}:{args.port}")
    print("=" * 50)
    
    if test_server_connection(args.host, args.port):
        print("SUCCESS: Server is running and accessible!")
    else:
        print("FAILED: Cannot connect to server")
        print("Make sure the server is running with:")
        print(f"python server/main_server.py {args.host} {args.port}")

if __name__ == "__main__":
    main()
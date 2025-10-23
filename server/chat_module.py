#!/usr/bin/env python3
"""
Chat Module - Handles group text chat using TCP
"""

import threading
import time
from datetime import datetime

class ChatModule:
    def __init__(self, server):
        self.server = server
        self.running = False
        self.chat_thread = None
        self.message_history = []
        self.max_history = 1000  # Keep last 1000 messages
        
    def start(self):
        """Start the chat module"""
        self.running = True
        self.chat_thread = threading.Thread(target=self.chat_loop, daemon=True)
        self.chat_thread.start()
        print("💬 Chat module started")
    
    def stop(self):
        """Stop the chat module"""
        self.running = False
        if self.chat_thread:
            self.chat_thread.join()
        print("💬 Chat module stopped")
    
    def chat_loop(self):
        """Main chat processing loop (placeholder for future features)"""
        while self.running:
            time.sleep(1)  # Simple loop for now
    
    def handle_message(self, username, message_data):
        """Handle incoming chat message"""
        if not self.running or username not in self.server.clients:
            return
        
        message_text = message_data.get('message', '').strip()
        if not message_text:
            return
        
        # Create formatted message
        chat_message = {
            'id': len(self.message_history) + 1,
            'username': username,
            'message': message_text,
            'timestamp': datetime.now().isoformat(),
            'type': 'chat'
        }
        
        # Add to history
        self.message_history.append(chat_message)
        
        # Keep only recent messages
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        # Broadcast to all clients
        self.broadcast_message(chat_message)
        
        print(f"💬 {username}: {message_text}")
    
    def broadcast_message(self, message):
        """Broadcast chat message to all clients"""
        broadcast_data = {
            'type': 'chat_message',
            'data': message
        }
        self.server.broadcast_to_all(broadcast_data)
    
    def broadcast_system_message(self, message):
        """Broadcast system message to all clients"""
        system_message = {
            'id': len(self.message_history) + 1,
            'username': 'SYSTEM',
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'type': 'system'
        }
        
        # Add to history
        self.message_history.append(system_message)
        
        # Broadcast
        broadcast_data = {
            'type': 'system_message',
            'data': system_message
        }
        self.server.broadcast_to_all(broadcast_data)
        
        print(f"🔔 SYSTEM: {message}")
    
    def get_message_history(self, limit=50):
        """Get recent message history"""
        return self.message_history[-limit:] if self.message_history else []
    
    def get_user_list(self):
        """Get list of online users"""
        return list(self.server.clients.keys())
    
    def send_private_message(self, from_username, to_username, message):
        """Send private message between users"""
        if to_username not in self.server.clients:
            return False
        
        private_message = {
            'id': len(self.message_history) + 1,
            'username': from_username,
            'message': f"[PRIVATE to {to_username}] {message}",
            'timestamp': datetime.now().isoformat(),
            'type': 'private',
            'recipient': to_username
        }
        
        # Add to history
        self.message_history.append(private_message)
        
        # Send to recipient
        broadcast_data = {
            'type': 'private_message',
            'data': private_message
        }
        self.server.send_to_client(to_username, broadcast_data)
        
        # Also send to sender for confirmation
        self.server.send_to_client(from_username, broadcast_data)
        
        print(f"💌 {from_username} -> {to_username}: {message}")
        return True

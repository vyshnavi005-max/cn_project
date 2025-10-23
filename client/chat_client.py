#!/usr/bin/env python3
"""
Chat Client - Handles group text chat
"""

import threading
import time
from datetime import datetime

class ChatClient:
    def __init__(self, main_client):
        self.main_client = main_client
        self.message_history = []
        self.max_history = 1000
        self.running = False
        self.chat_thread = None
        
    def start(self):
        """Start chat client"""
        self.running = True
        self.chat_thread = threading.Thread(target=self.chat_loop, daemon=True)
        self.chat_thread.start()
        print("💬 Chat client started")
    
    def stop(self):
        """Stop chat client"""
        self.running = False
        if self.chat_thread:
            self.chat_thread.join()
        print("💬 Chat client stopped")
    
    def chat_loop(self):
        """Main chat processing loop"""
        while self.running:
            time.sleep(1)  # Simple loop for now
    
    def send_message(self, message):
        """Send chat message to server"""
        if not self.main_client.connected:
            print("❌ Not connected to server")
            return False
        
        if not message.strip():
            return False
        
        # Add to local history
        local_message = {
            'id': len(self.message_history) + 1,
            'username': self.main_client.username,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'type': 'chat',
            'local': True
        }
        self.message_history.append(local_message)
        
        # Send to server
        self.main_client.send_chat_message(message)
        
        # Update GUI if available
        if self.main_client.main_window:
            self.main_client.main_window.update_chat_display()
        
        print(f"💬 Sent: {message}")
        return True
    
    def handle_message(self, message_data):
        """Handle incoming chat message from server"""
        try:
            # --- START CHANGE ---

            # Check if the message is from the current user
            # If so, we already added it locally in send_message, so skip adding it again.
            if message_data.get('username') == self.main_client.username:
                # Optional: You could potentially update the local message with server info
                # like a server-assigned ID or timestamp here if needed, but for
                # preventing duplicates, just returning is sufficient.
                print(f"DEBUG: Ignoring own broadcasted message.") # Optional debug print
                return # Don't add it again

            # --- END CHANGE ---

            # Add to history (only if it's from someone else)
            self.message_history.append(message_data)

            # Keep only recent messages
            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]

            # Update GUI if available
            if self.main_client.main_window:
                self.main_client.main_window.update_chat_display()

            # Print to console
            username = message_data.get('username', 'Unknown')
            message = message_data.get('message', '')
            # timestamp = message_data.get('timestamp', '') # Already handled in format_message_for_display

            print(f"💬 {username}: {message}") # Keep console log for received messages

        except Exception as e:
            print(f"❌ Error handling chat message: {e}")
    

    def handle_system_message(self, message_data):
        """Handle system message from server"""
        try:
            # Add to history
            self.message_history.append(message_data)
            
            # Update GUI if available
            if self.main_client.main_window:
                self.main_client.main_window.update_chat_display()
            
            # Print to console
            message = message_data.get('message', '')
            print(f"🔔 SYSTEM: {message}")
            
        except Exception as e:
            print(f"❌ Error handling system message: {e}")
    
    def get_message_history(self, limit=50):
        """Get recent message history"""
        return self.message_history[-limit:] if self.message_history else []
    
    def get_all_messages(self):
        """Get all message history"""
        return self.message_history.copy()
    
    def clear_history(self):
        """Clear message history"""
        self.message_history = []
        print("💬 Chat history cleared")
    
    def search_messages(self, query):
        """Search messages for specific text"""
        results = []
        query_lower = query.lower()
        
        for message in self.message_history:
            if query_lower in message.get('message', '').lower():
                results.append(message)
        
        return results
    
    def get_user_activity(self):
        """Get user activity statistics"""
        user_stats = {}
        
        for message in self.message_history:
            username = message.get('username', 'Unknown')
            if username not in user_stats:
                user_stats[username] = {
                    'message_count': 0,
                    'first_message': message.get('timestamp'),
                    'last_message': message.get('timestamp')
                }
            
            user_stats[username]['message_count'] += 1
            user_stats[username]['last_message'] = message.get('timestamp')
        
        return user_stats
    
    def format_message_for_display(self, message):
        """Format message for display in GUI"""
        try:
            username = message.get('username', 'Unknown')
            message_text = message.get('message', '')
            timestamp = message.get('timestamp', '')
            message_type = message.get('type', 'chat')
            
            # Parse timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                except:
                    time_str = timestamp
            else:
                time_str = 'Unknown'
            
            # Format based on message type
            if message_type == 'system':
                return f"[{time_str}] 🔔 {message_text}"
            elif message_type == 'private':
                return f"[{time_str}] 💌 {username}: {message_text}"
            else:
                return f"[{time_str}] {username}: {message_text}"
                
        except Exception as e:
            print(f"❌ Error formatting message: {e}")
            return f"Error formatting message: {str(e)}"
    
    def export_chat_history(self, filename):
        """Export chat history to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("LAN Communication Chat History\n")
                f.write("=" * 50 + "\n\n")
                
                for message in self.message_history:
                    formatted = self.format_message_for_display(message)
                    f.write(formatted + "\n")
            
            print(f"💬 Chat history exported to {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting chat history: {e}")
            return False

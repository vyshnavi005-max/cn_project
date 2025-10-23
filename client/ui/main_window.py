#!/usr/bin/env python3
"""
Main Window - GUI for the LAN Communication Client
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
import cv2
from PIL import Image, ImageTk

class MainWindow:
    def __init__(self, main_client):
        self.main_client = main_client
        self.root = None
        self.running = False
        
        # GUI components
        self.video_frame = None
        self.chat_frame = None
        self.file_frame = None
        self.screen_share_frame = None
        
        # Video display
        self.video_labels = {}  # {username: label}
        self.video_canvas = None
        
        # Chat display
        self.chat_text = None
        self.chat_entry = None
        self.user_list = None
        
        # File sharing
        self.file_listbox = None
        self.upload_button = None
        self.download_button = None
        
        # Screen sharing
        self.screen_share_label = None
        self.share_button = None
        self.stop_share_button = None
        
        # Status
        self.status_label = None
        
    def run(self):
        """Run the main GUI"""
        self.root = tk.Tk()
        self.root.title("LAN Communication Client")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.running = True
        
        # Start update loop
        self.update_loop()
        
        self.root.mainloop()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Create main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Video Conference Tab
        self.setup_video_tab(notebook)
        
        # Chat Tab
        self.setup_chat_tab(notebook)
        
        # File Sharing Tab
        self.setup_file_tab(notebook)
        
        # Screen Sharing Tab
        self.setup_screen_share_tab(notebook)
        
        # Status bar
        self.setup_status_bar()
    
    def setup_video_tab(self, notebook):
        """Setup video conference tab"""
        video_frame = ttk.Frame(notebook)
        notebook.add(video_frame, text="Video Conference")
        
        # Video controls
        controls_frame = ttk.Frame(video_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Start Camera", command=self.start_camera).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Stop Camera", command=self.stop_camera).pack(side=tk.LEFT, padx=5)
        
        # Quality controls
        ttk.Label(controls_frame, text="Quality:").pack(side=tk.LEFT, padx=(20, 5))
        self.quality_var = tk.IntVar(value=50)
        quality_scale = ttk.Scale(controls_frame, from_=1, to=100, variable=self.quality_var, orient=tk.HORIZONTAL)
        quality_scale.pack(side=tk.LEFT, padx=5)
        
        # Video display area
        self.video_canvas = tk.Canvas(video_frame, bg='black', height=400)
        self.video_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Video grid will be created dynamically
        self.video_frame = video_frame
    
    def setup_chat_tab(self, notebook):
        """Setup chat tab"""
        chat_frame = ttk.Frame(notebook)
        notebook.add(chat_frame, text="Chat")
        
        # Chat area
        chat_area_frame = ttk.Frame(chat_frame)
        chat_area_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Chat display
        self.chat_text = tk.Text(chat_area_frame, height=20, state=tk.DISABLED)
        chat_scrollbar = ttk.Scrollbar(chat_area_frame, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Chat input
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.chat_entry = ttk.Entry(input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind('<Return>', self.send_chat_message)
        
        ttk.Button(input_frame, text="Send", command=self.send_chat_message).pack(side=tk.RIGHT)
        
        # User list
        user_frame = ttk.LabelFrame(chat_frame, text="Online Users")
        user_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.user_list = tk.Listbox(user_frame, height=6)
        self.user_list.pack(fill=tk.X, padx=5, pady=5)
        
        self.chat_frame = chat_frame
    
    def setup_file_tab(self, notebook):
        """Setup file sharing tab"""
        file_frame = ttk.Frame(notebook)
        notebook.add(file_frame, text="File Sharing")
        
        # File controls
        controls_frame = ttk.Frame(file_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.upload_button = ttk.Button(controls_frame, text="Upload File", command=self.upload_file)
        self.upload_button.pack(side=tk.LEFT, padx=5)
        
        self.download_button = ttk.Button(controls_frame, text="Download Selected", command=self.download_file)
        self.download_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_file_list).pack(side=tk.LEFT, padx=5)
        
        # File list
        list_frame = ttk.LabelFrame(file_frame, text="Available Files")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame)
        file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=file_scrollbar.set)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(file_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_frame = file_frame
    
    def setup_screen_share_tab(self, notebook):
        """Setup screen sharing tab"""
        screen_frame = ttk.Frame(notebook)
        notebook.add(screen_frame, text="Screen Sharing")
        
        # Screen share controls
        controls_frame = ttk.Frame(screen_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.share_button = ttk.Button(controls_frame, text="Start Sharing", command=self.start_screen_sharing)
        self.share_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_share_button = ttk.Button(controls_frame, text="Stop Sharing", command=self.stop_screen_sharing, state=tk.DISABLED)
        self.stop_share_button.pack(side=tk.LEFT, padx=5)
        
        # Screen share display
        self.screen_share_label = ttk.Label(screen_frame, text="No screen sharing active", anchor=tk.CENTER)
        self.screen_share_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.screen_share_frame = screen_frame
    
    def setup_status_bar(self):
        """Setup status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="Disconnected", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
    
    def update_loop(self):
        """Main update loop for GUI"""
        if not self.running:
            return
        
        try:
            # Update video display
            self.update_video_display()
            
            # Update screen share display
            self.update_screen_share_display()
            
            # Update status
            self.update_status()
            
        except Exception as e:
            print(f"❌ Error in GUI update loop: {e}")
        
        # Schedule next update
        self.root.after(100, self.update_loop)  # Update every 100ms
    
    def start_camera(self):
        """Start camera capture"""
        if self.main_client.video_client:
            if self.main_client.video_client.start_camera():
                self.status_label.config(text="Camera started")
            else:
                messagebox.showerror("Error", "Failed to start camera")
    
    def stop_camera(self):
        """Stop camera capture"""
        if self.main_client.video_client:
            self.main_client.video_client.stop_camera()
            self.status_label.config(text="Camera stopped")
    
    def send_chat_message(self, event=None):
        """Send chat message"""
        message = self.chat_entry.get().strip()
        if message and self.main_client.chat_client:
            self.main_client.chat_client.send_message(message)
            self.chat_entry.delete(0, tk.END)
    
    def upload_file(self):
        """Upload file"""
        file_path = filedialog.askopenfilename()
        if file_path and self.main_client.file_client:
            self.main_client.file_client.upload_file(file_path)
    
    def download_file(self):
        """Download selected file"""
        selection = self.file_listbox.curselection()
        if selection and self.main_client.file_client:
            # Get file info from selection
            # This is simplified - in practice you'd store file info properly
            pass
    
    def refresh_file_list(self):
        """Refresh file list"""
        self.update_file_list()
    
    def start_screen_sharing(self):
        """Start screen sharing"""
        if self.main_client.screen_share_client:
            if self.main_client.screen_share_client.start_sharing():
                self.share_button.config(state=tk.DISABLED)
                self.stop_share_button.config(state=tk.NORMAL)
                self.status_label.config(text="Screen sharing started")
            else:
                messagebox.showerror("Error", "Failed to start screen sharing")
    
    def stop_screen_sharing(self):
        """Stop screen sharing"""
        if self.main_client.screen_share_client:
            self.main_client.screen_share_client.stop_sharing()
            self.share_button.config(state=tk.NORMAL)
            self.stop_share_button.config(state=tk.DISABLED)
            self.status_label.config(text="Screen sharing stopped")
    
    def update_video_display(self):
        """Update video display"""
        if not self.main_client.video_client:
            return
        
        try:
            # Get all frames (including local camera)
            frames = self.main_client.video_client.get_received_frames()
            
            # Clear canvas
            self.video_canvas.delete("all")
            
            if not frames:
                self.video_canvas.create_text(200, 200, text="No video streams", fill="white", font=("Arial", 16))
                return
            
            # Calculate grid layout
            num_frames = len(frames)
            cols = int((num_frames ** 0.5) + 0.5)
            rows = (num_frames + cols - 1) // cols
            
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return
            
            cell_width = canvas_width // cols
            cell_height = canvas_height // rows
            
            # Display frames
            for i, (username, frame_data) in enumerate(frames.items()):
                frame = frame_data['frame']
                
                row = i // cols
                col = i % cols
                
                x = col * cell_width
                y = row * cell_height
                
                # Resize frame to fit cell
                resized_frame = cv2.resize(frame, (cell_width, cell_height))
                
                # Convert to PhotoImage
                rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(pil_image)
                
                # Create image on canvas
                image_id = self.video_canvas.create_image(x + cell_width//2, y + cell_height//2, image=photo)
                
                # Add username label
                self.video_canvas.create_text(x + cell_width//2, y + cell_height - 20, 
                                            text=username, fill="white", font=("Arial", 12))
                
                # Store reference to prevent garbage collection
                self.video_canvas.image_refs = getattr(self.video_canvas, 'image_refs', [])
                self.video_canvas.image_refs.append(photo)
                
        except Exception as e:
            print(f"❌ Error updating video display: {e}")
    
    def update_chat_display(self):
        """Update chat display"""
        if not self.main_client.chat_client or not self.chat_text:
            return
        
        try:
            # Get recent messages
            messages = self.main_client.chat_client.get_message_history(50)
            
            # Clear and repopulate
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            
            for message in messages:
                formatted = self.main_client.chat_client.format_message_for_display(message)
                self.chat_text.insert(tk.END, formatted + "\n")
            
            self.chat_text.config(state=tk.DISABLED)
            self.chat_text.see(tk.END)
            
        except Exception as e:
            print(f"❌ Error updating chat display: {e}")
    
    def update_file_list(self):
        """Update file list"""
        if not self.main_client.file_client or not self.file_listbox:
            return
        
        try:
            # Clear listbox
            self.file_listbox.delete(0, tk.END)
            
            # Get available files
            files = self.main_client.file_client.get_available_files()
            
            for file_info in files:
                filename = file_info.get('filename', 'Unknown')
                uploader = file_info.get('uploader', 'Unknown')
                file_size = file_info.get('file_size', 0)
                size_str = self.main_client.file_client.format_file_size(file_size)
                
                display_text = f"{filename} ({size_str}) - {uploader}"
                self.file_listbox.insert(tk.END, display_text)
                
        except Exception as e:
            print(f"❌ Error updating file list: {e}")
    
    def update_screen_share_display(self):
        """Update screen share display"""
        if not self.main_client.screen_share_client or not self.screen_share_label:
            return
        
        try:
            current_frame = self.main_client.screen_share_client.get_current_frame()
            
            if current_frame:
                frame = current_frame['frame']
                presenter = current_frame['presenter']
                
                # Resize frame for display
                display_frame = cv2.resize(frame, (800, 600))
                
                # Convert to PhotoImage
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(pil_image)
                
                # Update label
                self.screen_share_label.config(image=photo, text="")
                self.screen_share_label.image = photo  # Keep reference
                
            else:
                self.screen_share_label.config(image="", text="No screen sharing active")
                
        except Exception as e:
            print(f"❌ Error updating screen share display: {e}")
    
    def update_user_list(self, users):
        """Update user list"""
        if not self.user_list:
            return
        
        try:
            # Clear listbox
            self.user_list.delete(0, tk.END)
            
            # Add users
            for user in users:
                username = user.get('username', 'Unknown')
                status = user.get('status', 'Unknown')
                self.user_list.insert(tk.END, f"{username} ({status})")
                
        except Exception as e:
            print(f"❌ Error updating user list: {e}")
    
    def update_status(self):
        """Update status bar"""
        if not self.status_label:
            return
        
        try:
            if self.main_client.connected:
                status = f"Connected as {self.main_client.username}"
                
                # Add module status
                if self.main_client.video_client and self.main_client.video_client.capturing:
                    status += " | Camera: ON"
                if self.main_client.screen_share_client and self.main_client.screen_share_client.is_sharing():
                    status += " | Sharing: ON"
                
                self.status_label.config(text=status)
            else:
                self.status_label.config(text="Disconnected")
                
        except Exception as e:
            print(f"❌ Error updating status: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        if self.main_client:
            self.main_client.disconnect()
        self.root.destroy()

#!/usr/bin/env python3
"""
Main Window - GUI for the LAN Communication Client
"""

#!/usr/bin/env python3
"""
Main Window - GUI for the LAN Communication Client
(Modified to use a thread-safe queue for updates)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
import cv2
from PIL import Image, ImageTk
import queue # <--- Import queue

class MainWindow:
    def __init__(self, main_client):
        self.main_client = main_client
        self.root = None
        self.running = False
        self.gui_update_queue = None # <--- Add placeholder for the queue

        # GUI components (Keep these as they were)
        self.video_frame = None
        self.chat_frame = None
        self.file_frame = None
        self.screen_share_frame = None
        self.video_labels = {}
        self.video_canvas = None
        self.chat_text = None
        self.chat_entry = None
        self.user_list = None
        self.file_listbox = None
        self.upload_button = None
        self.download_button = None
        self.screen_share_label = None
        self.share_button = None
        self.stop_share_button = None
        self.status_label = None
        # Add progress var back if needed
        self.progress_var = None
        self.progress_bar = None
        # Add quality var back
        self.quality_var = None


    def run(self):
        """Run the main GUI"""
        self.root = tk.Tk()
        self.root.title(f"LAN Comm Client - {self.main_client.username}") # Show username in title
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Ensure queue is set before setting up UI that might use it ---
        if not self.gui_update_queue:
             print("❌ ERROR: GUI Update Queue not set by main_client!")
             # You might want to raise an error or handle this more gracefully
             # For now, create a dummy queue to prevent immediate crashes in setup
             self.gui_update_queue = queue.Queue()


        self.setup_ui()
        self.running = True

        # Start the queue checking loop INSTEAD of the old update_loop
        self.check_gui_queue()

        print("GUI mainloop starting...")
        self.root.mainloop()
        print("GUI mainloop finished.") # This prints when the window closes

    # --- setup_ui and specific tab setup methods remain largely the same ---
    # Make sure setup_file_tab initializes progress_var and progress_bar
    # Make sure setup_video_tab initializes quality_var

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

    # --- Add back setup methods for video, chat, file, screen share, status bar ---
    # (These are mostly the same as your original file, ensure they create needed widgets)
    def setup_video_tab(self, notebook):
        """Setup video conference tab"""
        video_frame = ttk.Frame(notebook)
        notebook.add(video_frame, text="Video Conference")
        controls_frame = ttk.Frame(video_frame); controls_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(controls_frame, text="Start Camera", command=self.start_camera).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Stop Camera", command=self.stop_camera).pack(side=tk.LEFT, padx=5)
        ttk.Label(controls_frame, text="Quality:").pack(side=tk.LEFT, padx=(20, 5))
        self.quality_var = tk.IntVar(value=50) # Ensure this exists
        quality_scale = ttk.Scale(controls_frame, from_=1, to=100, variable=self.quality_var, orient=tk.HORIZONTAL, command=self.update_video_quality) # Add command
        quality_scale.pack(side=tk.LEFT, padx=5)
        self.video_canvas = tk.Canvas(video_frame, bg='black', height=400); self.video_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.video_frame = video_frame # Keep reference if needed

    def setup_chat_tab(self, notebook):
        """Setup chat tab"""
        chat_frame = ttk.Frame(notebook); notebook.add(chat_frame, text="Chat")
        chat_area_frame = ttk.Frame(chat_frame); chat_area_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_text = tk.Text(chat_area_frame, height=20, state=tk.DISABLED, wrap=tk.WORD) # Added wrap
        chat_scrollbar = ttk.Scrollbar(chat_area_frame, orient=tk.VERTICAL, command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        input_frame = ttk.Frame(chat_frame); input_frame.pack(fill=tk.X, padx=5, pady=5)
        self.chat_entry = ttk.Entry(input_frame); self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind('<Return>', self.send_chat_message)
        ttk.Button(input_frame, text="Send", command=self.send_chat_message).pack(side=tk.RIGHT)
        user_frame = ttk.LabelFrame(chat_frame, text="Online Users"); user_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5) # Changed fill/expand
        self.user_list = tk.Listbox(user_frame, height=6)
        user_scrollbar = ttk.Scrollbar(user_frame, orient=tk.VERTICAL, command=self.user_list.yview) # Added scrollbar
        self.user_list.configure(yscrollcommand=user_scrollbar.set)
        self.user_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5); user_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_frame = chat_frame # Keep reference if needed

    def setup_file_tab(self, notebook):
        """Setup file sharing tab"""
        file_frame = ttk.Frame(notebook); notebook.add(file_frame, text="File Sharing")
        controls_frame = ttk.Frame(file_frame); controls_frame.pack(fill=tk.X, padx=5, pady=5)
        self.upload_button = ttk.Button(controls_frame, text="Upload File", command=self.upload_file); self.upload_button.pack(side=tk.LEFT, padx=5)
        self.download_button = ttk.Button(controls_frame, text="Download Selected", command=self.download_file); self.download_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_file_list).pack(side=tk.LEFT, padx=5)
        list_frame = ttk.LabelFrame(file_frame, text="Available Files"); list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_listbox = tk.Listbox(list_frame)
        file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=file_scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.progress_var = tk.DoubleVar() # Ensure these exist
        self.progress_bar = ttk.Progressbar(file_frame, variable=self.progress_var, maximum=100); self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        self.file_frame = file_frame # Keep reference if needed

    def setup_screen_share_tab(self, notebook):
        """Setup screen sharing tab"""
        screen_frame = ttk.Frame(notebook); notebook.add(screen_frame, text="Screen Sharing")
        controls_frame = ttk.Frame(screen_frame); controls_frame.pack(fill=tk.X, padx=5, pady=5)
        self.share_button = ttk.Button(controls_frame, text="Start Sharing", command=self.start_screen_sharing); self.share_button.pack(side=tk.LEFT, padx=5)
        self.stop_share_button = ttk.Button(controls_frame, text="Stop Sharing", command=self.stop_screen_sharing, state=tk.DISABLED); self.stop_share_button.pack(side=tk.LEFT, padx=5)
        self.screen_share_label = ttk.Label(screen_frame, text="No screen sharing active", anchor=tk.CENTER, background='grey') # Added background
        self.screen_share_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.screen_share_frame = screen_frame # Keep reference if needed

    def setup_status_bar(self):
        """Setup status bar"""
        status_frame = ttk.Frame(self.root); status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text="Disconnected", relief=tk.SUNKEN, anchor=tk.W); self.status_label.pack(fill=tk.X, padx=5, pady=2)

    # --- REMOVE the old update_loop ---
    # def update_loop(self):
    #     # ... (Old code removed) ...

    # --- ADD the new queue checking loop ---
    def check_gui_queue(self):
        """ Check the queue for messages from other threads and process them. """
        if not self.running:
             return

        try:
            # Process all available messages in the queue
            while True:
                try:
                    message = self.gui_update_queue.get_nowait()
                    # Call the main client's handler function IN THE GUI THREAD
                    self.main_client.handle_server_message(message)

                    # --- Explicitly trigger updates that rely on background data ---
                    # These might become less necessary if handle_server_message updates everything,
                    # but kept for now for video/status polling.
                    self.update_video_display() # Polls video frames
                    self.update_screen_share_display() # Polls screen share frame
                    self.update_status() # Polls connection/module status

                except queue.Empty:
                    # No more messages in the queue right now
                    break # Exit the inner while loop
                except Exception as e:
                     print(f"❌ Error processing GUI queue message: {e}")
                     # Log the problematic message if possible
                     # print(f"Message was: {message}")

        except Exception as e:
            print(f"❌ Error in check_gui_queue: {e}")
        finally:
            # --- Schedule the next check ---
            # Make sure root exists before scheduling
            if self.running and self.root:
                 self.root.after(100, self.check_gui_queue) # Check again in 100ms

    # --- Button Command Methods (Keep as they were, ensure they call main_client methods) ---
    def start_camera(self):
        """Start camera capture"""
        if self.main_client.video_client:
            if self.main_client.video_client.start_camera():
                self.status_label.config(text="Camera started") # Direct update ok (response to user action)
            else:
                messagebox.showerror("Error", "Failed to start camera")

    def stop_camera(self):
        """Stop camera capture"""
        if self.main_client.video_client:
            self.main_client.video_client.stop_camera()
            self.status_label.config(text="Camera stopped") # Direct update ok

    # Add this new method for the quality slider
    def update_video_quality(self, value):
        """Callback for when the quality slider changes"""
        if self.main_client.video_client:
             quality_val = int(float(value)) # Scale value might be float
             self.main_client.video_client.set_quality(quality_val)
             # Optionally update status bar or log
             # print(f"Video quality set to {quality_val}")


    def send_chat_message(self, event=None):
        """Send chat message"""
        message = self.chat_entry.get().strip()
        if message and self.main_client.chat_client:
            # Sending is fine from GUI thread
            success = self.main_client.chat_client.send_message(message)
            if success:
                 self.chat_entry.delete(0, tk.END)
            else:
                 messagebox.showwarning("Send Error", "Failed to send message.")
                 # Might indicate connection issue

    def upload_file(self):
        """Show file dialog and initiate upload"""
        file_path = filedialog.askopenfilename()
        if file_path and self.main_client.file_client:
            print(f"Selected file for upload: {file_path}")
            # Initiating upload is fine from GUI thread
            success = self.main_client.file_client.upload_file(file_path)
            if not success:
                 messagebox.showerror("Upload Error", "Failed to initiate file upload.")

    def download_file(self):
        """Download selected file"""
        selection_indices = self.file_listbox.curselection()
        if not selection_indices:
             messagebox.showinfo("Download", "Please select a file from the list to download.")
             return

        if self.main_client.file_client:
            selected_index = selection_indices[0]
            # Need a way to map the listbox index back to the file_id
            available_files = self.main_client.file_client.get_available_files()
            if selected_index < len(available_files):
                 file_info = available_files[selected_index]
                 file_id = file_info.get('file_id')
                 filename = file_info.get('filename')
                 if file_id:
                      print(f"Initiating download for file ID: {file_id} ({filename})")
                      success = self.main_client.file_client.download_file(file_id)
                      if not success:
                           messagebox.showerror("Download Error", f"Failed to initiate download for {filename}.")
                 else:
                      messagebox.showerror("Download Error", "Could not get file ID for selected item.")
            else:
                 messagebox.showerror("Download Error", "Selected index out of range (list might be outdated). Try refreshing.")

    def refresh_file_list(self):
        """Refresh file list (Maybe request list from server?)"""
        # For now, just calls update based on current client state
        print("Refreshing file list display...")
        self.update_file_list()

    def start_screen_sharing(self):
        """Start screen sharing"""
        if self.main_client.screen_share_client:
            # Starting is fine from GUI thread
            if self.main_client.screen_share_client.start_sharing():
                self.share_button.config(state=tk.DISABLED)
                self.stop_share_button.config(state=tk.NORMAL)
                self.status_label.config(text="Screen sharing started") # Direct update ok
            else:
                messagebox.showerror("Error", "Failed to start screen sharing")

    def stop_screen_sharing(self):
        """Stop screen sharing"""
        if self.main_client.screen_share_client:
            # Stopping is fine from GUI thread
            self.main_client.screen_share_client.stop_sharing()
            self.share_button.config(state=tk.NORMAL)
            self.stop_share_button.config(state=tk.DISABLED)
            self.status_label.config(text="Screen sharing stopped") # Direct update ok

    # --- GUI Update Methods (Called from check_gui_queue or handle_server_message) ---
    # These should now primarily use data passed via the queue or directly from main_client state
    # if that state is updated *by the GUI thread* via handle_server_message

    def update_video_display(self):
        """Update video display (Called periodically by check_gui_queue)"""
        # This function still relies on polling frames. More advanced: video client
        # could put frames onto a dedicated video queue.
        if not self.running or not self.main_client.video_client or not self.video_canvas:
            return

        try:
            # Get latest frames (copy is important if background thread updates it)
            frames_dict = self.main_client.video_client.get_received_frames()

            # Clear previous images and references
            self.video_canvas.delete("all")
            self.video_canvas.image_refs = [] # Clear old refs

            if not frames_dict:
                # Get canvas size AFTER window is potentially drawn
                w = self.video_canvas.winfo_width()
                h = self.video_canvas.winfo_height()
                if w > 1 and h > 1:
                    self.video_canvas.create_text(w//2, h//2, text="No video streams", fill="white", font=("Arial", 16))
                return

            num_frames = len(frames_dict)
            cols = int(num_frames**0.5 + 0.999) # Calculate columns for roughly square grid
            rows = (num_frames + cols - 1) // cols

            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                return # Canvas not ready

            cell_width = max(1, canvas_width // cols)
            cell_height = max(1, canvas_height // rows)

            frame_items = list(frames_dict.items()) # Get items to iterate with index

            for i in range(num_frames):
                username, frame_data = frame_items[i]
                frame = frame_data.get('frame')

                if frame is None: continue # Skip if frame data missing

                row = i // cols
                col = i % cols

                x_center = col * cell_width + cell_width // 2
                y_center = row * cell_height + cell_height // 2

                # Resize frame maintaining aspect ratio to fit cell
                img_h, img_w = frame.shape[:2]
                scale = min(cell_width / img_w, cell_height / img_h) if img_w > 0 and img_h > 0 else 1
                new_w, new_h = int(img_w * scale), int(img_h * scale)

                if new_w <= 0 or new_h <= 0: continue # Skip invalid size

                try:
                    resized_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)
                    photo = ImageTk.PhotoImage(pil_image)

                    # Create image on canvas
                    self.video_canvas.create_image(x_center, y_center, image=photo)
                    # Add username label below image
                    self.video_canvas.create_text(x_center, y_center + new_h // 2 + 10,
                                                text=username, fill="yellow", font=("Arial", 10))

                    # Store reference MUST be done here
                    self.video_canvas.image_refs.append(photo)

                except Exception as e_inner:
                     print(f"❌ Error processing frame for {username}: {e_inner}")


        except Exception as e:
            # Avoid crashing the GUI loop if there's an error here
            print(f"❌ Error updating video display: {e}")

    def update_chat_display(self):
        """Update chat display (Called when chat messages arrive via queue)"""
        # This function should ideally be called ONLY by handle_server_message
        # when a chat or system message is processed.
        if not self.running or not self.main_client.chat_client or not self.chat_text:
            return

        try:
            messages = self.main_client.chat_client.get_all_messages() # Get full history for redraw

            # Determine if scrollbar is currently at the bottom
            # scroll_pos = self.chat_text.yview()[1]
            # at_bottom = scroll_pos >= 1.0

            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)

            for message in messages:
                formatted = self.main_client.chat_client.format_message_for_display(message)
                self.chat_text.insert(tk.END, formatted + "\n")

            self.chat_text.config(state=tk.DISABLED)
            # Scroll to bottom only if it was already near the bottom
            # if at_bottom:
            self.chat_text.see(tk.END)

        except Exception as e:
            print(f"❌ Error updating chat display: {e}")

    def update_file_list(self):
        """Update file list (Called when file list changes via queue)"""
        # This should ideally be called by handle_server_message when 'file_available' is processed.
        if not self.running or not self.main_client.file_client or not self.file_listbox:
            return

        try:
            self.file_listbox.delete(0, tk.END)
            files = self.main_client.file_client.get_available_files()

            for idx, file_info in enumerate(files):
                filename = file_info.get('filename', 'Unknown')
                uploader = file_info.get('uploader', 'Unknown')
                file_size = file_info.get('file_size', 0)
                size_str = self.main_client.file_client.format_file_size(file_size)
                # Store the index or file_id implicitly? For simplicity, index is used.
                display_text = f"[{idx}] {filename} ({size_str}) - Up by: {uploader}"
                self.file_listbox.insert(tk.END, display_text)

        except Exception as e:
            print(f"❌ Error updating file list: {e}")

    # Add this method to handle progress updates from file_client
    def update_download_progress(self, file_id_or_index, progress_percent):
         """Updates the progress bar based on download progress."""
         # This should be called safely from the GUI thread (e.g., via handle_server_message or queue)
         if self.progress_bar and self.progress_var:
              self.progress_var.set(progress_percent)


    def update_screen_share_display(self):
        """Update screen share display (Called periodically or when frame arrives via queue)"""
        # Similar to video, relies on polling for now.
        if not self.running or not self.main_client.screen_share_client or not self.screen_share_label:
            return

        try:
            current_frame_info = self.main_client.screen_share_client.get_current_frame()

            if current_frame_info:
                frame = current_frame_info.get('frame')
                presenter = current_frame_info.get('presenter', 'Unknown')

                if frame is None:
                    # Clear display if frame is None even if info exists
                    self.screen_share_label.config(image="", text=f"Waiting for frame from {presenter}...")
                    self.screen_share_label.image = None
                    return

                # Resize frame to fit label space (maintaining aspect ratio)
                label_w = self.screen_share_label.winfo_width()
                label_h = self.screen_share_label.winfo_height()

                if label_w <= 1 or label_h <= 1: return # Label not ready

                img_h, img_w = frame.shape[:2]
                scale = min(label_w / img_w, label_h / img_h) if img_w > 0 and img_h > 0 else 1
                # Only downscale, don't upscale beyond original (optional)
                # scale = min(scale, 1.0)
                new_w, new_h = int(img_w * scale), int(img_h * scale)

                if new_w <= 0 or new_h <= 0: return # Skip invalid size

                display_frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

                # Convert to PhotoImage
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(pil_image)

                # Update label
                self.screen_share_label.config(image=photo, text=f"Sharing by: {presenter}") # Show presenter name
                self.screen_share_label.image = photo # Keep reference

            else:
                # No frame info, clear display
                self.screen_share_label.config(image="", text="No screen sharing active")
                self.screen_share_label.image = None

        except Exception as e:
            print(f"❌ Error updating screen share display: {e}")


    def update_user_list(self, users_data):
        """Update user list (Called when user list update arrives via queue)"""
        # This should be called ONLY by handle_server_message when 'user_list_update' is processed.
        if not self.running or not self.user_list:
            return

        try:
            self.user_list.delete(0, tk.END)
            for user_info in users_data:
                username = user_info.get('username', 'Unknown')
                status = user_info.get('status', 'Unknown')
                display = f"{username} ({status})"
                self.user_list.insert(tk.END, display)
        except Exception as e:
            print(f"❌ Error updating user list: {e}")

    def update_status(self):
        """Update status bar (Called periodically)"""
        if not self.running or not self.status_label:
            return

        try:
            status_text = "Disconnected"
            if self.main_client.connected:
                status_text = f"Connected as {self.main_client.username}"
                # Add module status indicators
                cam_status = "OFF"
                if self.main_client.video_client and self.main_client.video_client.capturing:
                     cam_status = "ON"
                status_text += f" | Cam: {cam_status}"

                sharing_status = "OFF"
                if self.main_client.screen_share_client:
                     if self.main_client.screen_share_client.is_sharing():
                          sharing_status = "SHARING"
                     elif self.main_client.screen_share_client.is_viewing():
                           sharing_status = "VIEWING"
                status_text += f" | Screen: {sharing_status}"

            self.status_label.config(text=status_text)
        except Exception as e:
            print(f"❌ Error updating status: {e}")

    def on_closing(self):
        """Handle window closing"""
        print("Window close requested.")
        self.running = False # Signal loops to stop
        if self.main_client:
            self.main_client.disconnect() # Attempt graceful disconnect
        if self.root:
             self.root.destroy() # Close the Tkinter window
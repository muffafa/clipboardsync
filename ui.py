### ui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from device_manager import DeviceStatus

class NotificationManager:
    def __init__(self, root):
        self.root = root
        self.notifications = []
        self.notification_window = None
        
    def show(self, title, message):
        self.notifications.append((title, message))
        self.root.after(100, self._process_notifications)
        
    def _process_notifications(self):
        if not self.notifications:
            return
            
        title, message = self.notifications.pop(0)
        
        if self.notification_window:
            self.notification_window.destroy()
            
        self.notification_window = tk.Toplevel(self.root)
        self.notification_window.overrideredirect(True)
        self.notification_window.attributes('-topmost', True)
        
        # Position in bottom right corner
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 300
        height = 100
        x = screen_width - width - 20
        y = screen_height - height - 60
        self.notification_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Style the notification
        self.notification_window.configure(bg="#f0f0f0", bd=1, relief="solid")
        frame = ttk.Frame(self.notification_window, padding=10)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text=title, font=("Arial", 12, "bold")).pack(anchor="w")
        ttk.Label(frame, text=message, wraplength=280).pack(anchor="w", pady=(5, 0))
        
        # Auto-close after 3 seconds
        self.root.after(3000, self._close_notification)
        
    def _close_notification(self):
        if self.notification_window:
            self.notification_window.destroy()
            self.notification_window = None
            
        # Process next notification if any
        if self.notifications:
            self.root.after(100, self._process_notifications)

class ClipboardSyncUI:
    def __init__(self, device_manager, network_manager):
        self.device_manager = device_manager
        self.network_manager = network_manager
        
        self.root = tk.Tk()
        self.root.title("Clipboard Sync")
        self.root.geometry("500x600")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Apply better styling
        style = ttk.Style()
        style.theme_use("clam")  # Modern-looking theme
        
        # Configure colors
        self.colors = {
            "paired": "#4CAF50",      # Green
            "discovered": "#FFC107",  # Yellow
            "disconnected": "#F44336" # Red
        }
        
        # Create UI components first
        self._create_ui()
        
        # Register callbacks AFTER UI components are created
        self.device_manager.register_device_updates_callback(self._update_device_list)
        self.device_manager.register_pairing_callback(self._handle_pairing_request)
        
        # Create notification manager
        self.notification_manager = NotificationManager(self.root)
        self.network_manager.register_notification_callback(self.notification_manager.show)
        
    def _create_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Create your device section
        self._create_your_device_section(main_frame)
        
        # Create device list section
        self._create_device_list_section(main_frame)
        
        # Update device list initially
        self._update_device_list()
        
    def _create_your_device_section(self, parent):
        device_frame = ttk.LabelFrame(parent, text="This Device", padding=10)
        device_frame.pack(fill="x", pady=(0, 10))
        
        # Device info
        info_frame = ttk.Frame(device_frame)
        info_frame.pack(fill="x", pady=5)
        
        ttk.Label(info_frame, text="Hostname:").grid(row=0, column=0, sticky="w", padx=5)
        self.hostname_label = ttk.Label(info_frame, text=self.network_manager.hostname)
        self.hostname_label.grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(info_frame, text="IP Address:").grid(row=1, column=0, sticky="w", padx=5)
        self.ip_label = ttk.Label(info_frame, text=self.network_manager.local_ip)
        self.ip_label.grid(row=1, column=1, sticky="w", padx=5)
        
        # Status indicator
        ttk.Label(info_frame, text="Status:").grid(row=2, column=0, sticky="w", padx=5)
        self.status_frame = ttk.Frame(info_frame)
        self.status_frame.grid(row=2, column=1, sticky="w", padx=5)
        
        self.status_indicator = tk.Canvas(self.status_frame, width=15, height=15, bg=self.colors["paired"], bd=0, highlightthickness=0)
        self.status_indicator.pack(side="left", padx=(0, 5))
        self.status_label = ttk.Label(self.status_frame, text="Active")
        self.status_label.pack(side="left")
        
        # Controls frame
        controls_frame = ttk.Frame(device_frame)
        controls_frame.pack(fill="x", pady=5)
        
        # Pairing toggle
        self.pairing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls_frame, 
            text="Enable Pairing", 
            variable=self.pairing_var,
            command=self._toggle_pairing
        ).pack(side="left", padx=5)
        
        # Sync toggle
        self.sync_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            controls_frame, 
            text="Enable Syncing", 
            variable=self.sync_var,
            command=self._toggle_sync
        ).pack(side="left", padx=5)
        
    def _create_device_list_section(self, parent):
        devices_frame = ttk.LabelFrame(parent, text="Nearby Devices", padding=10)
        devices_frame.pack(fill="both", expand=True)
        
        # Scrollable frame for devices
        scroll_container = ttk.Frame(devices_frame)
        scroll_container.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(scroll_container)
        scrollbar.pack(side="right", fill="y")
        
        # Canvas and inner frame for scrolling
        self.devices_canvas = tk.Canvas(scroll_container, yscrollcommand=scrollbar.set)
        self.devices_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.devices_canvas.yview)
        
        self.devices_inner_frame = ttk.Frame(self.devices_canvas)
        self.devices_canvas_window = self.devices_canvas.create_window((0, 0), window=self.devices_inner_frame, anchor="nw")
        
        # Update scrollregion when frame size changes
        self.devices_inner_frame.bind("<Configure>", self._on_frame_configure)
        self.devices_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Refresh button
        refresh_button = ttk.Button(devices_frame, text="Refresh", command=self._update_device_list)
        refresh_button.pack(side="bottom", pady=(5, 0))
        
    def _on_frame_configure(self, event):
        self.devices_canvas.configure(scrollregion=self.devices_canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        # Update the window width when canvas resizes
        self.devices_canvas.itemconfig(self.devices_canvas_window, width=event.width)
        
    def _update_device_list(self):
        # Check if UI components are initialized
        if not hasattr(self, 'devices_inner_frame') or not self.devices_inner_frame.winfo_exists():
            # UI is not ready yet, schedule an update for later
            self.root.after(100, self._update_device_list)
            return
            
        # Clear existing widgets
        for widget in self.devices_inner_frame.winfo_children():
            widget.destroy()
            
        devices = list(self.device_manager.devices.values())
        
        # Sort devices: Paired first, then discovered, then disconnected
        devices.sort(key=lambda d: (
            0 if d.status == DeviceStatus.PAIRED else
            1 if d.status == DeviceStatus.DISCOVERED else 2,
            d.hostname
        ))
        
        if not devices:
            ttk.Label(self.devices_inner_frame, text="No devices found. Ensure pairing is enabled.").pack(pady=10)
            return
            
        for device in devices:
            self._create_device_widget(device)
            
    def _create_device_widget(self, device):
        # Create frame for this device
        device_frame = ttk.Frame(self.devices_inner_frame)
        device_frame.pack(fill="x", pady=5, padx=5)
        
        # Add border and padding
        container = ttk.LabelFrame(
            device_frame, 
            text=f"{device.hostname} ({device.ip})",
            padding=10
        )
        container.pack(fill="x")
        
        # Status indicator
        status_frame = ttk.Frame(container)
        status_frame.pack(fill="x", pady=(0, 5))
        
        # Status color
        status_color = self.colors.get(device.status, self.colors["disconnected"])
        status_indicator = tk.Canvas(status_frame, width=15, height=15, bg=status_color, bd=0, highlightthickness=0)
        status_indicator.pack(side="left", padx=(0, 5))
        
        # Status text
        status_label = ttk.Label(status_frame, text=device.status.capitalize())
        status_label.pack(side="left")
        
        # Last seen
        last_seen_text = "Online" if device.is_active() else f"Last seen: {time.strftime('%H:%M:%S', time.localtime(device.last_seen))}"
        last_seen_label = ttk.Label(status_frame, text=last_seen_text)
        last_seen_label.pack(side="right")
        
        # Controls frame
        controls_frame = ttk.Frame(container)
        controls_frame.pack(fill="x", pady=5)
        
        # Show appropriate controls based on device status
        if device.status == DeviceStatus.PAIRED:
            # Send toggle
            send_var = tk.BooleanVar(value=device.send_enabled)
            ttk.Checkbutton(
                controls_frame, 
                text="Send Clipboard", 
                variable=send_var,
                command=lambda: self.device_manager.set_send_enabled(device.ip, send_var.get())
            ).pack(side="left", padx=5)
            
            # Receive toggle
            receive_var = tk.BooleanVar(value=device.receive_enabled)
            ttk.Checkbutton(
                controls_frame, 
                text="Receive Clipboard", 
                variable=receive_var,
                command=lambda: self.device_manager.set_receive_enabled(device.ip, receive_var.get())
            ).pack(side="left", padx=5)
            
            # Manual send button
            ttk.Button(
                controls_frame,
                text="Send Now",
                command=lambda: self.network_manager.send_clipboard_to_device(device.ip)
            ).pack(side="left", padx=5)
            
            # Disconnect button
            ttk.Button(
                controls_frame,
                text="Disconnect",
                command=lambda: self._disconnect_device(device.ip)
            ).pack(side="right", padx=5)
            
        elif device.status == DeviceStatus.DISCOVERED and not device.pairing_pending:
            # Connect button for discovered devices
            ttk.Button(
                controls_frame,
                text="Request Pairing",
                command=lambda: self._request_pairing(device.ip)
            ).pack(side="left", padx=5)
            
        elif device.status == DeviceStatus.DISCOVERED and device.pairing_pending:
            ttk.Label(controls_frame, text="Pairing request pending...").pack(side="left", padx=5)
            
        elif device.status == DeviceStatus.DISCONNECTED:
            # Try reconnect button
            ttk.Button(
                controls_frame,
                text="Attempt Reconnect",
                command=lambda: self._request_pairing(device.ip)
            ).pack(side="left", padx=5)
            
            # Remove button
            ttk.Button(
                controls_frame,
                text="Remove",
                command=lambda: self.device_manager.remove_device(device.ip)
            ).pack(side="right", padx=5)
    
    def _toggle_pairing(self):
        enabled = self.pairing_var.get()
        self.network_manager.discovery_enabled = enabled
        
        if enabled:
            self.status_indicator.config(bg=self.colors["paired"])
            self.status_label.config(text="Active")
        else:
            self.status_indicator.config(bg=self.colors["disconnected"])
            self.status_label.config(text="Inactive")
            
    def _toggle_sync(self):
        enabled = self.sync_var.get()
        self.network_manager.sync_enabled = enabled
        
    def _request_pairing(self, ip):
        device = self.device_manager.get_device(ip)
        if device and device.manually_disconnected:
            # Clear the manual disconnect flag when explicitly requesting pairing
            device.manually_disconnected = False
            
        self.network_manager._request_pairing(ip)
        
    def _disconnect_device(self, ip):
        if messagebox.askyesno("Disconnect Device", "Are you sure you want to disconnect this device?"):
            self.device_manager.disconnect_device(ip)
        
    def _handle_pairing_request(self, ip, hostname):
        # Called when a pairing request is received
        result = messagebox.askyesno(
            "Pairing Request",
            f"Accept pairing request from {hostname} ({ip})?",
            icon=messagebox.QUESTION
        )
        
        # Send response
        self.network_manager.send_pairing_response(ip, result)
        
    def _on_close(self):
        self.network_manager.stop()
        self.root.destroy()
        
    def start(self):
        self.root.mainloop()

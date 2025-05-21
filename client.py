### client.py

import socket
import pyperclip
import time
import threading
from config import PORT, UDP_BROADCAST_PORT, BROADCAST_INTERVAL, BUFFER_SIZE
import tkinter as tk
from tkinter import ttk

class Device:
    def __init__(self, ip, hostname="Unknown"):
        self.ip = ip
        self.hostname = hostname
        self.send_enabled = False
        self.receive_enabled = False
        self.last_seen = time.time()

    def update_seen(self):
        self.last_seen = time.time()

devices = {}  # ip -> Device
last_sent = ""


def broadcast_presence():
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = b"CLIPBOARDSYNC_DISCOVERY"
            sock.sendto(message, ("<broadcast>", UDP_BROADCAST_PORT))
        time.sleep(BROADCAST_INTERVAL)

def listen_for_peers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", UDP_BROADCAST_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                ip = addr[0]
                if data == b"CLIPBOARDSYNC_DISCOVERY":
                    if ip not in devices:
                        devices[ip] = Device(ip)
                    devices[ip].update_seen()
            except:
                continue

def send_clipboard_content(text):
    for device in devices.values():
        if device.send_enabled:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((device.ip, PORT))
                    s.sendall(text.encode("utf-8"))
                    print(f"[CLIENT] Sent clipboard to {device.ip}: {text}")
            except Exception as e:
                print(f"[CLIENT] Failed to send to {device.ip}: {e}")

def monitor_clipboard():
    global last_sent
    while True:
        current_text = pyperclip.paste()
        if current_text and current_text != last_sent:
            send_clipboard_content(current_text)
            last_sent = current_text
        time.sleep(1)

def update_device_list(frame):
    for widget in frame.winfo_children():
        widget.destroy()
    for ip, device in devices.items():
        container = ttk.LabelFrame(frame, text=f"{device.hostname} ({ip})")
        container.pack(fill="x", padx=5, pady=5)

        send_var = tk.BooleanVar(value=device.send_enabled)
        recv_var = tk.BooleanVar(value=device.receive_enabled)

        def toggle_send(var=send_var, dev=device):
            dev.send_enabled = var.get()

        def toggle_recv(var=recv_var, dev=device):
            dev.receive_enabled = var.get()

        ttk.Checkbutton(container, text="Send Clipboard", variable=send_var, command=toggle_send).pack(anchor="w")
        ttk.Checkbutton(container, text="Receive Clipboard", variable=recv_var, command=toggle_recv).pack(anchor="w")

def start_ui():
    root = tk.Tk()
    root.title("Clipboard Sync")
    root.geometry("400x500")

    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    label = ttk.Label(main_frame, text="Discovered Devices:")
    label.pack(anchor="w")

    devices_frame = ttk.Frame(main_frame)
    devices_frame.pack(fill="both", expand=True)

    def refresh():
        update_device_list(devices_frame)
        root.after(3000, refresh)

    refresh()
    root.mainloop()
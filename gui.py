import threading
import tkinter as tk
from tkinter import messagebox
import socket
import pyperclip
import time
from config import PORT, UDP_BROADCAST_PORT, BROADCAST_INTERVAL, BUFFER_SIZE

discovered_peers = set()
last_sent = ""
running = False

def broadcast_presence():
    while running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                message = b"CLIPBOARDSYNC_DISCOVERY"
                sock.sendto(message, ("<broadcast>", UDP_BROADCAST_PORT))
        except:
            pass
        time.sleep(BROADCAST_INTERVAL)

def listen_for_peers():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("", UDP_BROADCAST_PORT))
        while running:
            try:
                data, addr = sock.recvfrom(1024)
                if data == b"CLIPBOARDSYNC_DISCOVERY":
                    discovered_peers.add(addr[0])
            except:
                continue

def send_clipboard_content(text):
    for ip in discovered_peers:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, PORT))
                s.sendall(text.encode("utf-8"))
        except:
            pass

def handle_client(conn, addr):
    last_received = ""
    while running:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            text = data.decode("utf-8")
            if text != last_received:
                pyperclip.copy(text)
                last_received = text
        except:
            break
    conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        while running:
            try:
                s.settimeout(1)
                conn, addr = s.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue

def monitor_clipboard():
    global last_sent
    while running:
        current_text = pyperclip.paste()
        if current_text and current_text != last_sent:
            send_clipboard_content(current_text)
            last_sent = current_text
        time.sleep(1)

class ClipboardSyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clipboard Sync")
        self.geometry("300x150")

        self.status_var = tk.StringVar(value="Disconnected")
        self.peers_var = tk.StringVar(value="Peers: 0")

        tk.Label(self, textvariable=self.status_var).pack(pady=10)
        tk.Label(self, textvariable=self.peers_var).pack()

        self.connect_button = tk.Button(self, text="Connect", command=self.connect)
        self.connect_button.pack(pady=5)

        self.disconnect_button = tk.Button(self, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.pack()

        self.update_ui()

    def update_ui(self):
        self.peers_var.set(f"Peers: {len(discovered_peers)}")
        if running:
            self.status_var.set("Connected")
        else:
            self.status_var.set("Disconnected")
        self.after(1000, self.update_ui)

    def connect(self):
        global running
        if running:
            messagebox.showinfo("Info", "Already connected")
            return
        running = True
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)

        threading.Thread(target=broadcast_presence, daemon=True).start()
        threading.Thread(target=listen_for_peers, daemon=True).start()
        threading.Thread(target=start_server, daemon=True).start()
        threading.Thread(target=monitor_clipboard, daemon=True).start()

    def disconnect(self):
        global running
        running = False
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = ClipboardSyncApp()
    app.mainloop()

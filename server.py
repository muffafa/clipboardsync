### server.py

import socket
import threading
import pyperclip
from config import PORT, BUFFER_SIZE

class DeviceManager:
    def __init__(self):
        self.receive_enabled = {}  # ip -> bool

    def is_allowed(self, ip):
        return self.receive_enabled.get(ip, False)

    def set_receive(self, ip, allow):
        self.receive_enabled[ip] = allow

device_manager = DeviceManager()

last_received = ""

def handle_client(conn, addr):
    global last_received
    ip = addr[0]
    print(f"Connected by {addr}")
    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            text = data.decode("utf-8")
            if text != last_received and device_manager.is_allowed(ip):
                last_received = text
                pyperclip.copy(text)
                print(f"[SERVER] Clipboard updated from {addr}: {text}")
        except Exception as e:
            print(f"[SERVER] Error with {addr}: {e}")
            break
    conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        print(f"[SERVER] Listening on port {PORT}...")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


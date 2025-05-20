
### client.py

import socket
import pyperclip
import time
import threading
from config import PORT, UDP_BROADCAST_PORT, BROADCAST_INTERVAL, BUFFER_SIZE

discovered_peers = set()
last_sent = ""

def broadcast_presence():
    while True:
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
        while True:
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
            continue

def monitor_clipboard():
    global last_sent
    while True:
        current_text = pyperclip.paste()
        if current_text and current_text != last_sent:
            send_clipboard_content(current_text)
            last_sent = current_text
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=broadcast_presence, daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()
    monitor_clipboard()

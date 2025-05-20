### server.py

import socket
import threading
import pyperclip
from config import PORT, BUFFER_SIZE

last_received = ""

def handle_client(conn, addr):
    global last_received
    while True:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            text = data.decode("utf-8")
            if text != last_received:
                last_received = text
                pyperclip.copy(text)
        except:
            break
    conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()


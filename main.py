### main.py

import threading
from server import start_server
from client import broadcast_presence, listen_for_peers, monitor_clipboard, start_ui

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=broadcast_presence, daemon=True).start()
    threading.Thread(target=listen_for_peers, daemon=True).start()
    threading.Thread(target=monitor_clipboard, daemon=True).start()
    start_ui()

### main.py
import threading
from device_manager import DeviceManager
from network import NetworkManager
from ui import ClipboardSyncUI

if __name__ == "__main__":
    # Initialize components
    device_manager = DeviceManager()
    network_manager = NetworkManager(device_manager)
    
    # Start network manager
    network_manager.start()
    
    # Start UI
    ui = ClipboardSyncUI(device_manager, network_manager)
    ui.start()
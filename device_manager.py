### device_manager.py
import time
import socket
import threading
import json
import os
from message import Message, MessageType

class DeviceStatus:
    DISCOVERED = "discovered"
    PAIRED = "paired" 
    DISCONNECTED = "disconnected"

class Device:
    def __init__(self, ip, hostname="Unknown"):
        self.ip = ip
        self.hostname = hostname
        self.send_enabled = False
        self.receive_enabled = False
        self.last_seen = time.time()
        self.status = DeviceStatus.DISCOVERED
        self.pairing_pending = False
        self.manually_disconnected = False
        
    def update_seen(self):
        self.last_seen = time.time()
        
    def is_active(self, timeout=15):
        return (time.time() - self.last_seen) < timeout
        
    def to_dict(self):
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "send_enabled": self.send_enabled,
            "receive_enabled": self.receive_enabled,
            "last_seen": self.last_seen,
            "status": self.status,
            "pairing_pending": self.pairing_pending,
            "manually_disconnected": self.manually_disconnected
        }
        
class DeviceManager:
    def __init__(self):
        self.devices = {}  # ip -> Device
        self.pairing_callbacks = []
        self.device_updates_callbacks = []
        self.devices_lock = threading.RLock()
        self.pairing_enabled = True
        self.load_paired_devices()
        
    def register_pairing_callback(self, callback):
        self.pairing_callbacks.append(callback)
        
    def register_device_updates_callback(self, callback):
        self.device_updates_callbacks.append(callback)
        
    def notify_device_updates(self):
        for callback in self.device_updates_callbacks:
            callback()
            
    def get_device(self, ip):
        with self.devices_lock:
            return self.devices.get(ip)
            
    def add_or_update_device(self, ip, hostname="Unknown", status=None):
        with self.devices_lock:
            if ip not in self.devices:
                self.devices[ip] = Device(ip, hostname)
                if status:
                    self.devices[ip].status = status
            else:
                self.devices[ip].update_seen()
                if hostname != "Unknown":
                    self.devices[ip].hostname = hostname
                if status:
                    self.devices[ip].status = status
            
            self.notify_device_updates()
            return self.devices[ip]
            
    def remove_device(self, ip):
        with self.devices_lock:
            if ip in self.devices:
                del self.devices[ip]
                self.notify_device_updates()
                
    def get_active_devices(self):
        active_devices = []
        with self.devices_lock:
            for ip, device in self.devices.items():
                if device.is_active():
                    active_devices.append(device)
        return active_devices
        
    def set_send_enabled(self, ip, enabled):
        with self.devices_lock:
            if ip in self.devices:
                self.devices[ip].send_enabled = enabled
                self.save_paired_devices()
                self.notify_device_updates()
                
    def set_receive_enabled(self, ip, enabled):
        with self.devices_lock:
            if ip in self.devices:
                self.devices[ip].receive_enabled = enabled
                self.save_paired_devices()
                self.notify_device_updates()
                
    def is_allowed_to_send(self, ip):
        with self.devices_lock:
            device = self.devices.get(ip)
            return device and device.status == DeviceStatus.PAIRED and device.receive_enabled
            
    def can_send_to(self, ip):
        with self.devices_lock:
            device = self.devices.get(ip)
            return device and device.status == DeviceStatus.PAIRED and device.send_enabled
        
    def handle_pairing_request(self, sender_ip, sender_name):
        for callback in self.pairing_callbacks:
            callback(sender_ip, sender_name)
            
    def accept_pairing(self, ip):
        with self.devices_lock:
            if ip in self.devices:
                self.devices[ip].status = DeviceStatus.PAIRED
                self.devices[ip].pairing_pending = False
                self.save_paired_devices()
                self.notify_device_updates()
                return True
            return False
            
    def reject_pairing(self, ip):
        with self.devices_lock:
            if ip in self.devices:
                self.devices[ip].pairing_pending = False
                self.notify_device_updates()
                
    def disconnect_device(self, ip):
        with self.devices_lock:
            if ip in self.devices:
                self.devices[ip].status = DeviceStatus.DISCONNECTED
                self.devices[ip].send_enabled = False
                self.devices[ip].receive_enabled = False
                # Add a flag to prevent auto-reconnection from discovery
                self.devices[ip].manually_disconnected = True
                self.save_paired_devices()
                self.notify_device_updates()
                
    def save_paired_devices(self):
        paired_devices = {}
        with self.devices_lock:
            for ip, device in self.devices.items():
                if device.status == DeviceStatus.PAIRED or device.manually_disconnected:
                    paired_devices[ip] = {
                        "hostname": device.hostname,
                        "send_enabled": device.send_enabled,
                        "receive_enabled": device.receive_enabled,
                        "manually_disconnected": device.manually_disconnected
                    }
        
        try:
            config_dir = os.path.expanduser("~/.clipboardsync")
            os.makedirs(config_dir, exist_ok=True)
            with open(os.path.join(config_dir, "paired_devices.json"), "w") as f:
                json.dump(paired_devices, f)
        except Exception as e:
            print(f"Error saving paired devices: {e}")
            
    def load_paired_devices(self):
        try:
            config_file = os.path.expanduser("~/.clipboardsync/paired_devices.json")
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    paired_devices = json.load(f)
                    
                with self.devices_lock:
                    for ip, device_data in paired_devices.items():
                        device = Device(ip, device_data.get("hostname", "Unknown"))
                        device.status = DeviceStatus.DISCONNECTED  # Start as disconnected until seen
                        device.send_enabled = device_data.get("send_enabled", False)
                        device.receive_enabled = device_data.get("receive_enabled", False)
                        device.manually_disconnected = device_data.get("manually_disconnected", False)
                        self.devices[ip] = device
        except Exception as e:
            print(f"Error loading paired devices: {e}")

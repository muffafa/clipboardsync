### network.py
import socket
import threading
import time
import pyperclip
from config import PORT, UDP_BROADCAST_PORT, PAIRING_PORT, BROADCAST_INTERVAL, BUFFER_SIZE, DEVICE_TIMEOUT
from message import Message, MessageType
from device_manager import DeviceStatus

def get_local_hostname():
    try:
        return socket.gethostname()
    except:
        return "Unknown"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

class NetworkManager:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.local_ip = get_local_ip()
        self.hostname = get_local_hostname()
        self.discovery_enabled = True
        self.sync_enabled = True
        self.last_sent_clipboard = ""
        self.running = True
        self.notification_callbacks = []
        
    def register_notification_callback(self, callback):
        self.notification_callbacks.append(callback)
        
    def notify(self, title, message):
        for callback in self.notification_callbacks:
            callback(title, message)
            
    def start(self):
        # Start all network threads
        threading.Thread(target=self._broadcast_presence, daemon=True).start()
        threading.Thread(target=self._listen_for_discovery, daemon=True).start()
        threading.Thread(target=self._listen_for_pairing, daemon=True).start()
        threading.Thread(target=self._clipboard_server, daemon=True).start()
        threading.Thread(target=self._monitor_clipboard, daemon=True).start()
        threading.Thread(target=self._check_device_timeouts, daemon=True).start()
        
    def stop(self):
        self.running = False
        
    def _broadcast_presence(self):
        """Broadcasts device presence for discovery"""
        while self.running:
            if self.discovery_enabled:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    msg = Message(
                        MessageType.DISCOVERY,
                        {},
                        self.local_ip,
                        self.hostname
                    )
                    try:
                        sock.sendto(msg.to_json().encode("utf-8"), ("<broadcast>", UDP_BROADCAST_PORT))
                    except Exception as e:
                        print(f"Broadcast error: {e}")
            time.sleep(BROADCAST_INTERVAL)
            
    def _listen_for_discovery(self):
        """Listens for discovery broadcasts from other devices"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", UDP_BROADCAST_PORT))
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(BUFFER_SIZE)
                    ip = addr[0]
                    
                    if ip == self.local_ip:
                        continue
                        
                    try:
                        message = Message.from_json(data.decode("utf-8"))
                        if not message or message.type != MessageType.DISCOVERY:
                            continue
                            
                        device = self.device_manager.get_device(ip)
                        if device and device.status == DeviceStatus.PAIRED:
                            # Already paired device, just update last seen
                            self.device_manager.add_or_update_device(ip, message.sender_name)
                        elif device and device.status == DeviceStatus.DISCONNECTED and not device.manually_disconnected:
                            # Previously paired and not manually disconnected, now reconnected
                            self.device_manager.add_or_update_device(ip, message.sender_name, DeviceStatus.PAIRED)
                            self.notify("Device Reconnected", f"{message.sender_name} ({ip}) is back online")
                        elif not device and self.discovery_enabled:
                            # New device discovered
                            self.device_manager.add_or_update_device(ip, message.sender_name)
                            # Automatically request pairing
                            self._request_pairing(ip)
                            
                    except Exception as e:
                        print(f"Error processing discovery from {ip}: {e}")
                        
                except Exception as e:
                    print(f"Discovery listener error: {e}")
    
    def _request_pairing(self, ip):
        """Send pairing request to a device"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((ip, PAIRING_PORT))
                msg = Message(
                    MessageType.PAIRING_REQUEST,
                    {},
                    self.local_ip,
                    self.hostname
                )
                sock.sendall(msg.to_json().encode("utf-8"))
                self.notify("Pairing Request Sent", f"Sent pairing request to {ip}")
        except Exception as e:
            print(f"Error sending pairing request to {ip}: {e}")
            
    def _listen_for_pairing(self):
        """Listen for pairing requests and responses"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("", PAIRING_PORT))
            server.listen(5)
            server.settimeout(1)  # Allow checking self.running
            
            while self.running:
                try:
                    conn, addr = server.accept()
                    threading.Thread(target=self._handle_pairing_connection, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Pairing server error: {e}")
                    time.sleep(1)
                    
    def _handle_pairing_connection(self, conn, addr):
        """Handle an incoming pairing connection"""
        try:
            conn.settimeout(5)
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return
                
            message = Message.from_json(data.decode("utf-8"))
            if not message:
                return
                
            ip = addr[0]
            
            if message.type == MessageType.PAIRING_REQUEST:
                # Received pairing request
                if self.discovery_enabled:
                    device = self.device_manager.add_or_update_device(ip, message.sender_name)
                    device.pairing_pending = True
                    self.device_manager.handle_pairing_request(ip, message.sender_name)
                
            elif message.type == MessageType.PAIRING_RESPONSE:
                # Received response to our pairing request
                accepted = message.data.get("accepted", False)
                if accepted:
                    self.device_manager.add_or_update_device(ip, message.sender_name, DeviceStatus.PAIRED)
                    self.notify("Pairing Accepted", f"{message.sender_name} ({ip}) accepted your pairing request")
                else:
                    self.notify("Pairing Rejected", f"{message.sender_name} ({ip}) rejected your pairing request")
                    
        except Exception as e:
            print(f"Error handling pairing from {addr}: {e}")
        finally:
            conn.close()
            
    def send_pairing_response(self, ip, accepted):
        """Send response to a pairing request"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((ip, PAIRING_PORT))
                msg = Message(
                    MessageType.PAIRING_RESPONSE,
                    {"accepted": accepted},
                    self.local_ip,
                    self.hostname
                )
                sock.sendall(msg.to_json().encode("utf-8"))
                
                if accepted:
                    self.device_manager.accept_pairing(ip)
                    self.notify("Pairing Completed", f"You are now paired with {ip}")
                else:
                    self.device_manager.reject_pairing(ip)
        except Exception as e:
            print(f"Error sending pairing response to {ip}: {e}")
            
    def _clipboard_server(self):
        """Server to receive clipboard data"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("", PORT))
            server.listen(5)
            server.settimeout(1)  # Allow checking self.running
            
            while self.running:
                try:
                    conn, addr = server.accept()
                    threading.Thread(target=self._handle_clipboard_connection, args=(conn, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Clipboard server error: {e}")
                    time.sleep(1)
                    
    def _handle_clipboard_connection(self, conn, addr):
        """Handle incoming clipboard data"""
        try:
            ip = addr[0]
            conn.settimeout(5)
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return
                
            message = Message.from_json(data.decode("utf-8"))
            if not message or message.type != MessageType.CLIPBOARD_DATA:
                return
                
            if not self.sync_enabled:
                print(f"Ignoring clipboard from {ip}: sync disabled")
                return
                
            if not self.device_manager.is_allowed_to_send(ip):
                print(f"Ignoring clipboard from {ip}: not allowed to send")
                return
                
            text = message.data.get("text", "")
            if text != self.last_sent_clipboard:
                pyperclip.copy(text)
                device = self.device_manager.get_device(ip)
                hostname = device.hostname if device else "Unknown"
                self.notify("Clipboard Updated", f"Received clipboard from {hostname} ({ip})")
                
        except Exception as e:
            print(f"Error handling clipboard from {addr}: {e}")
        finally:
            conn.close()
            
    def send_clipboard_to_device(self, ip):
        """Send clipboard to a specific device"""
        text = pyperclip.paste()
        self._send_clipboard_to_ip(ip, text)
        
    def _send_clipboard_to_ip(self, ip, text):
        """Send clipboard text to specific IP"""
        if not text:
            return
            
        if not self.device_manager.can_send_to(ip):
            return
            
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((ip, PORT))
                
                msg = Message(
                    MessageType.CLIPBOARD_DATA,
                    {"text": text},
                    self.local_ip,
                    self.hostname
                )
                sock.sendall(msg.to_json().encode("utf-8"))
                
                device = self.device_manager.get_device(ip)
                hostname = device.hostname if device else "Unknown"
                self.notify("Clipboard Sent", f"Sent clipboard to {hostname} ({ip})")
                
        except Exception as e:
            print(f"Failed to send clipboard to {ip}: {e}")
            
    def _monitor_clipboard(self):
        """Monitor clipboard for changes and send to paired devices"""
        while self.running:
            if self.sync_enabled:
                current_text = pyperclip.paste()
                if current_text and current_text != self.last_sent_clipboard:
                    self.last_sent_clipboard = current_text
                    # Send to all devices that are enabled for sending
                    for device in self.device_manager.get_active_devices():
                        if device.status == DeviceStatus.PAIRED and device.send_enabled:
                            self._send_clipboard_to_ip(device.ip, current_text)
            time.sleep(1)
            
    def _check_device_timeouts(self):
        """Check for devices that haven't been seen recently"""
        while self.running:
            active_devices = self.device_manager.get_active_devices()
            all_devices = list(self.device_manager.devices.values())
            
            for device in all_devices:
                if not device.is_active(DEVICE_TIMEOUT) and device.status == DeviceStatus.PAIRED:
                    # Mark as disconnected
                    device.status = DeviceStatus.DISCONNECTED
                    self.notify("Device Disconnected", f"{device.hostname} ({device.ip}) is now offline")
                    self.device_manager.notify_device_updates()
                    
            time.sleep(5)
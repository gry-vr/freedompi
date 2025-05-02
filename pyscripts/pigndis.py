"""import serial
import time
import socket

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't have to be reachable
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except:
        ip = "0.0.0.0"
    finally:
        s.close()
    return ip

def main():
    ser = serial.Serial('/dev/ttyACM2', 115200, timeout=1)
    time.sleep(2)  # Wait for Arduino to reset

    last_ip = ""
    while True:
        ip = get_ip()
        if ip != last_ip:
            msg = f"\\nWiFi connected\\n\\nip:{ip}\n"
            ser.write(msg.encode('utf-8'))
            last_ip = ip
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()

"""

import serial
import time
import socket
import fcntl
import struct
import os

def get_ip_address(interface):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_addr = socket.inet_ntoa(
            fcntl.ioctl(
                sock.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', bytes(interface[:15], 'utf-8'))
            )[20:24]
        )
        return ip_addr
    except Exception:
        return None

def main():
    ser = serial.Serial('/dev/ttyACM2', 115200, timeout=1)
    time.sleep(2)  # Give Arduino time to boot

    last_message = ""
    while True:
        wifi_ip = get_ip_address('wlan0')
        eth_ip = get_ip_address('eth0')

        if wifi_ip is None:
            wifi_ip = "Disconnected"
        if eth_ip is None:
            eth_ip = "Disconnected"

        message = f"\\nWAN: {wifi_ip}\\nLAN: {eth_ip}\n"

        if message != last_message:
            ser.write(message.encode('utf-8'))
            print(f"Sent to Arduino: {message.strip()}")
            last_message = message

        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    main()

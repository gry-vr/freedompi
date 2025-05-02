# -*- coding: utf-8 -*-
import sys
import re
from serial.tools.list_ports import comports
import time
import can
import cantools
import threading
from pymavlink import mavutil
import struct



def find_ports_by_vid(vid):
    """Return a list of /dev/tty* names whose VID matches `vid`."""
    matches = []
    for port in comports():
        # direct attribute match
        if port.vid == vid:
            matches.append(port.device)
            continue
        # fallback: parse VID from hwid string
        hwid = port.hwid or ""
        m = re.search(r"VID:PID=(?P<vid>[0-9A-Fa-f]+):", hwid)
        if m and int(m.group("vid"), 16) == vid:
            matches.append(port.device)
    return matches



# === Setup ===
CAN_TX_INTERFACE = 'can0'  # Send throttle command on can0
CAN_RX_INTERFACE = 'can1'  # Read vehicle data from can1
CAN_ID_TX = 0x200
DBC_FILE = 'j1939_FFW_v3.dbc'
TARGET_VID = 0x2DAE         # Cube Orange Plus vendor ID
BAUD       = 57600          # telemetry baud rate
HB_TIMEOUT = 5              # seconds to wait for heartbeat


# Load DBC file
dbc = cantools.database.load_file(DBC_FILE)

# Connect to MAVLink
hb = None
while True:
    try:
        ports = find_ports_by_vid(TARGET_VID)
        for port in ports:
            print("Trying to connect to MAVLink...")
            mav = mavutil.mavlink_connection(port, baud=57600, autoreconnect=False)
            hb = mav.recv_match(type='HEARTBEAT', blocking=True, timeout=HB_TIMEOUT)
            if hb:
                break
            else:
                mav.close()
            print("MAVLink connection established!")
        if hb:
            break
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5)

# IMPORTANT: after this connection, rename correctly:


# Connect to CAN buses
print("Connecting to CAN TX (can0)...")
bus_tx = can.interface.Bus(channel=CAN_TX_INTERFACE, interface='socketcan')
print("CAN TX ready.")

print("Connecting to CAN RX (can1)...")
bus_rx = can.interface.Bus(channel=CAN_RX_INTERFACE, interface='socketcan')
print("CAN RX ready.")

# ARC counter for outgoing messages
arc_counter = 0

# === Utility Functions ===
def calculate_checksum(can_id, data, arc):
    checksum_sum = sum(data[:7])
    checksum_sum += arc & 0x0F
    checksum_sum += (can_id & 0xFF)
    checksum_sum += ((can_id >> 8) & 0xFF)
    checksum_sum += ((can_id >> 16) & 0xFF)
    checksum_sum += ((can_id >> 24) & 0xFF)
    checksum = (((checksum_sum >> 6) & 0x03) + (checksum_sum >> 3) + checksum_sum) & 0x07
    return checksum

def pack_checksum_and_arc(arc, checksum):
    return ((checksum & 0x0F) << 4) | (arc & 0x0F)

def send_mavlink_param(name, value):
    mav.mav.param_set_send(
        mav.target_system,
        mav.target_component,
        name.encode('utf-8'),
        float(value),
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )

# === Outgoing CAN from MAVLink ===
def forward_mavlink_to_can():
    global arc_counter, mavlink_connection, bus_tx
    ENG_ON_C = 0
    START_C = 0
    TSC = 0
    ARM_C = 0
    AIR_TEST_C = 0
    can_data = [
            ENG_ON_C & 0xFF,
            START_C & 0xFF,
            ARM_C & 0xFF,
            AIR_TEST_C & 0xFF,
            0xF1,
            TSC & 0xFF,
            (TSC >> 8) & 0xFF,
            0x00  # Placeholder for checksum + ARC
            ]
    fake_data = [
            0xF1,
            TSC &0xFF,
            (TSC >> 8) & 0xFF,
            0xFF,

            0xFF,
            0xFF,
            0xFF,
            0xFF, 
            ]

    while True:
        msg = mav.recv_match(type='SERVO_OUTPUT_RAW', blocking=False)
        if msg:
            ENG_ON = msg.servo1_raw
            START = msg.servo2_raw
            TSC_raw = msg.servo3_raw
            ARM = msg.servo7_raw
            AIR_TEST = msg.servo6_raw

            if TSC_raw < 1000:
                mapped_speed = 0
            elif TSC_raw > 2000:
                mapped_speed = 30800
            else:
                mapped_speed = int((TSC_raw - 1000) / 1000 * 30800)

            TSC = mapped_speed
            ENG_ON_C = ENG_ON if ENG_ON > 1500 else 0
            START_C = START if START > 1500 else 0
            ARM_C = ARM if ARM > 1500 else 0 
            AIR_TEST_C = AIR_TEST if AIR_TEST > 1500 else 0 
            can_data = [
                ENG_ON_C & 0xFF,
                START_C & 0xFF,
                ARM_C & 0xFF,
                AIR_TEST_C   & 0xFF,
                0xF1,
                TSC & 0xFF,
                (TSC >> 8) & 0xFF,
                0x00  # Placeholder for checksum + ARC
            ]
            
            fake_data[1] = can_data[5]
            fake_data[2] = can_data[6]
            arc_counter = (arc_counter + 1) % 8
            arc = arc_counter & 0x0F
            checksum = calculate_checksum(0x0C000031, fake_data, arc)
            can_data[7] = pack_checksum_and_arc(arc, checksum)

            message = can.Message(arbitration_id=CAN_ID_TX, data=can_data, is_extended_id=False)
            try:
                bus_tx.send(message)
                print(f"[CAN TX] Sent: {' '.join(f'{b:02X}' for b in can_data)}")
            except can.CanError as e:
                print(f"CAN send error: {e}")

        elif msg == None:
            arc_counter = (arc_counter + 1) % 8
            arc = arc_counter & 0x0F
            fake_data[1] = can_data[5]
            fake_data[2] = can_data[6]
            checksum = calculate_checksum(0x0C000031, fake_data, arc)
            can_data[7] = pack_checksum_and_arc(arc, checksum)

            message = can.Message(arbitration_id=CAN_ID_TX, data=can_data, is_extended_id=False)
            try:
                bus_tx.send(message)
                print(f"[CAN TX] Sent: {' '.join(f'{b:02X}' for b in can_data)}")
            except can.CanError as e:
                print(f"CAN send error: {e}")

        time.sleep(0.010)

"""# === Incoming CAN to MAVLink ===
def forward_can_to_mavlink():
    message = bus_rx.recv(timeout=0.00001)
    if message:
        try:
            decoded = dbc.decode_message(message.arbitration_id, message.data)
            print(f"[CAN RX] {message.arbitration_id:#04x}: {decoded}")

            signal_map = {
                "EngOilPress": "SCR_USER1",
                "EngIntakeManifold1Press": "SCR_USER2",
                "EngCoolantTemp": "SCR_USER3",
                "Engine_Speed": "SCR_USER4",
                "Keyswitch_Battery_Potential__158": "SCR_USER5",
                "Engine_Turbocharger_1_Turbine_Ou": "SCR_USER6"
            }

            for signal, param in signal_map.items():
                if signal in decoded:
                    value = decoded[signal]
                    send_mavlink_param(param, value)
                    print(f"[CAN ? MAVLink] {param} = {value}")
                else:
                    value = 99
                    send_mavlink_param(param, value)
                    print(f"[CAN ? MAVLink] {param} = {value}")

        except Exception as e:
            print(f"Error decoding CAN message: {e}")
"""
# === Incoming CAN to MAVLink ===
def forward_can_to_mavlink():
    signal_map = {
        "EngOilPress": "SCR_USER1",
        "EngIntakeManifold1Press": "SCR_USER2",
        "EngCoolantTemp": "SCR_USER3",
        "Engine_Speed": "SCR_USER4",
        "Keyswitch_Battery_Potential__158": "SCR_USER5",
        "Engine_Turbocharger_1_Turbine_Ou": "SCR_USER6"
    }

    # This will remember the latest decoded values
    latest_signals = {signal: 99 for signal in signal_map.keys()}  # Default = 99

    while True:
        try:
            message = bus_rx.recv(timeout=1.0)  # Wait up to 1 second
            if message is None:
                # No new message, send all "latest" values
                for signal, param in signal_map.items():
                    send_mavlink_param(param, latest_signals[signal])
                    print(f"[CAN ? MAVLink] (timeout) {param} = {latest_signals[signal]:.2f}")
                continue

            try:
                decoded = dbc.decode_message(message.arbitration_id, message.data)
                print(f"[CAN RX] {message.arbitration_id:#04x}: {decoded}")

                # Update signals if found
                for signal, param in signal_map.items():
                    if signal in decoded:
                        value = decoded[signal]
                        latest_signals[signal] = value  # Save good value
                        send_mavlink_param(param, value)
                        print(f"[CAN ? MAVLink] {param} = {value:.2f}")

            except Exception as decode_error:
                print(f"[CAN RX] Decode Error: {decode_error}")

        except Exception as e:
            print(f"[CAN RX] General Error: {e}")

# === Main Loop ===
def main():
    command_throttle_thread = threading.Thread(
        target=forward_mavlink_to_can
        )
    command_throttle_thread.start()
    print("Forwarding between MAVLink and CAN...")
    while True:
        #forward_mavlink_to_can()
        forward_can_to_mavlink()
        time.sleep(0.07)
    command_throttle_thread.join()

if __name__ == '__main__':
    main()

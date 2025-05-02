#!/bin/bash

# Log file
LOGFILE="/home/droyd/startup_debug.log"

# Start logging
echo "[$(date)] pignstartup.sh started via cron" >> "$LOGFILE"

# Wait until a real IP address is available
echo "[$(date)] Waiting for network IP..." >> "$LOGFILE"
until /usr/bin/hostname -I | /usr/bin/grep -v '^127' > /dev/null; do
    sleep 2
done

IP=$(/usr/bin/hostname -I | /usr/bin/awk '{print $1}')
echo "[$(date)] Network IP acquired: $IP" >> "$LOGFILE"

# Bring up CAN interfaces
echo "[$(date)] Setting up CAN interfaces..." >> "$LOGFILE"
/sbin/ip link set can0 down >> "$LOGFILE" 2>&1
/sbin/ip link set can0 up type can bitrate 500000 >> "$LOGFILE" 2>&1 || echo "can0 failed" >> "$LOGFILE"
/sbin/ip link set can1 down >> "$LOGFILE" 2>&1
/sbin/ip link set can1 up type can bitrate 500000 >> "$LOGFILE" 2>&1 || echo "can1 failed" >> "$LOGFILE"

/bin/sleep 2

# Start pigndis.py using system Python
echo "[$(date)] Starting pigndis.py..." >> "$LOGFILE"
/usr/bin/python3 /home/droyd/pigndis.py >> "$LOGFILE" 2>&1 &

# Start pignmavcan.py using virtualenv Python
echo "[$(date)] Starting pignmavcan.py from venv..." >> "$LOGFILE"
/home/droyd/mavproxy-venv/bin/python /home/droyd/pignmavcan.py >> "$LOGFILE" 2>&1 &

echo "[$(date)] pignstartup.sh completed." >> "$LOGFILE"

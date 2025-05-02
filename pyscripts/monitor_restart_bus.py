import os
import time
import subprocess
import psutil 
import datetime
import threading

CAN_INTERFACE="can0"


def check_can_status(interface):
    try:
        result = subprocess.run(
                    ["ip", "-details", "-statistics", "link", "show",interface],
                    capture_output=True,
                    text=True
                )
        if "state BUS-OFF" in result.stdout:
            return False
        return True
    except Exception as e:
        print(f"Error checking can status {e}")


def reset_can_interface(interface):
    try:
        subprocess.run(
                ["sudo", "ip", "link", "set", interface, "down"]
                )
        time.sleep(0.4)
        subprocess.run(["sudo", "ip", "link", "set", interface, "up"])
        primt(f"{interface} brought back up ")
    except Exception as e:
        print(f"Error resetting {e}")


def monitor_canbus(interval=0.3):
    while True:
        if not check_can_status(CAN_INTERFACE):
            print(f"{CAN_INTERFACE} is off")
            reset_can_interface(CAN_INTERFACE)
        else:
            print("active")
        time.sleep(interval)


def make_unique_log_name():
    time_stamp = datetime.datetime.now()
    return time_stamp.strftime("%m-%d_%H-%M-%S")

def get_temps():
    temps = psutil.sensors_temperatures()
    if not temps:
        return None

    core_temps = temps.get('coretemp')
    temp = core_temps[1].current
#    print(temp)
    if core_temps:
        return temp

    return {k: [e.current for e in v] for k, v in temps.items()}

def log_temps():
    time_stamp = make_unique_log_name()

    with open(f"temp_{time_stamp}.log", "w") as log_file:
        while True:
            log_file.write(f"{datetime.datetime.now().strftime('%H-%M-%S')}")
            log_file.write(f" {get_temps()}")
            log_file.write("\n")
            time.sleep(1)
            print("hey")

# there is some benefit to me going ahead and throwing this into a thread.
# I wonder ...
if __name__=="__main__":
    monitor = threading.Thread(target=monitor_canbus)
    logging = threading.Thread(target=log_temps)

    monitor.start()
    logging.start()


import socket
import subprocess
import time
import psutil


def is_simulation_running():
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if 'python' in proc.info['name']:
            if any('tello_drone_final.py' in cmd for cmd in proc.info['cmdline']):
                return True
    return False


def start_simulation():
   
    print("[INFO] Starting Tello simulation...")
    subprocess.Popen(["python", "tello_drone_final.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_simulation(timeout=30):
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(('localhost', 9999), timeout=1):
                print("[INFO] Simulation is ready!")
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    print("[ERROR] Simulation did not start in time.")
    return False


def send_command(command):
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect(('localhost', 9999))
        client.send(command.encode())



if not is_simulation_running():
    start_simulation()
    if not wait_for_simulation():
        print("[ERROR] Simulation failed to start.")
        exit(1)
else:
    print("[INFO] Simulation already running.")

# Sequence of drone actions
print("Connecting...")
send_command("connect")
time.sleep(2)

print("Takeoff...")
send_command("takeoff")
time.sleep(5)


print("Landing...")
send_command("land")

print("[INFO] Drone flight sequence complete.")

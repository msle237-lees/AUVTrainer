from pynput import keyboard
import numpy as np

from auvtrainer.client.requests import DBApiClient

# from auvtrainer.client.requests impor

PRESSED_KEYS = list()
FORCE = 25
ROTATION_FORCE = 10
COMMAND = np.zeros(5)
CLIENT = DBApiClient("http://localhost:8000")


def on_press(key):
    global PRESSED_KEYS
    if hasattr(key, 'char'):
        PRESSED_KEYS.append(key.char)
        PRESSED_KEYS = list(set(PRESSED_KEYS))

def on_release(key):
    global PRESSED_KEYS
    if hasattr(key, 'char'):
        PRESSED_KEYS.remove(key.char)

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

def get_keyboard_input():
    """
        Commands breakdown:
        [
            W/S: Forward/Backward (X axis)
            A/D: Left/Right (Y axis)
            I/K: Up/Down (Z axis)
            J/L: Yaw Left/Right (Rotation around Z axis)
            
            Arm is by default 1 for keyboard input

            q: Quit
            c: Clear Database
        ]
    """
    global COMMAND
    COMMAND = np.zeros(5)

    if 'w' in PRESSED_KEYS:
        COMMAND[0] += FORCE
    if 's' in PRESSED_KEYS:
        COMMAND[0] -= FORCE
    if 'a' in PRESSED_KEYS:
        COMMAND[1] += FORCE
    if 'd' in PRESSED_KEYS:
        COMMAND[1] -= FORCE
    if 'i' in PRESSED_KEYS:
        COMMAND[2] += FORCE
    if 'k' in PRESSED_KEYS:
        COMMAND[2] -= FORCE
    if 'j' in PRESSED_KEYS:
        COMMAND[3] += ROTATION_FORCE
    if 'l' in PRESSED_KEYS:
        COMMAND[3] -= ROTATION_FORCE

    if 'q' in PRESSED_KEYS:
        print("Quitting keyboard input listener.")
        listener.stop()
        exit(0)

    COMMAND[4] = 1  # Arm is always 1 for keyboard input

    return COMMAND

def send_keyboard_input(command : np.ndarray):
    global CLIENT
    input_data = {
        "x": int(command[0]),
        "y": int(command[1]),
        "z": int(command[2]),
        "yaw": int(command[3]),
        "arm": bool(command[4]),
    }

    response = CLIENT.table_append("inputs", input_data)
    return response

def keyboard_run():
    import time
    while True:
        cmd = get_keyboard_input()
        print(f"Sending command: {cmd}")
        send_keyboard_input(cmd)
        time.sleep(0.01)

if __name__ == "__main__":
    keyboard_run()

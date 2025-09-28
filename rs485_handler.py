#!/usr/bin/env python3
"""
RS-485 Handler Module
- Listens for incoming RS485 messages in the background
- Provides function to send messages from web app
- Ensures GPIO cleanup so pins are never left 'busy'
"""
import time
import serial
import threading
import RPi.GPIO as GPIO

# --- RS485 config ---
RS485_DE_BCM = 6          # GPIO6 controls DE/RE (HIGH=TX, LOW=RX)
SERIAL_PORT = "/dev/serial0"
BAUD = 9600

# --- Globals ---
last_message = None
_running = True

# Initialize serial (open once and reuse)
ser = serial.Serial(
    port=SERIAL_PORT,
    baudrate=BAUD,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
)

def init_gpio():
    """Setup DE/RE control pin for RS485 transceiver."""
    # Release the pin first in case it's stuck as 'busy'
    try:
        GPIO.cleanup(RS485_DE_BCM)
    except Exception:
        pass
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RS485_DE_BCM, GPIO.OUT, initial=GPIO.LOW)  # default RX

def _listen_loop():
    """Background thread: read incoming RS485 messages."""
    global last_message
    while _running:
        try:
            if ser.in_waiting:
                msg = ser.readline().decode("utf-8", errors="replace").strip()
                if msg:
                    print("RX:", msg)
                    last_message = msg
        except Exception as e:
            print("RS485 read error:", e)
            time.sleep(1)

def start_listener():
    """Start background listener thread (non-blocking)."""
    t = threading.Thread(target=_listen_loop, daemon=True)
    t.start()

def get_last_message():
    """Return most recent RX message (or None)."""
    return last_message

def send_message(msg: str):
    """Send a message over RS485 (string)."""
    try:
        GPIO.output(RS485_DE_BCM, GPIO.HIGH)  # enable TX
        time.sleep(0.01)
        ser.write((msg + "\n").encode())
        ser.flush()
        GPIO.output(RS485_DE_BCM, GPIO.LOW)   # back to RX
        print("TX:", msg)
        return True
    except Exception as e:
        print("RS485 send error:", e)
        return False

def cleanup():
    """Stop listener, close serial, release GPIO."""
    global _running
    _running = False
    try:
        ser.close()
    except Exception:
        pass
    try:
        GPIO.cleanup(RS485_DE_BCM)
    except Exception:
        pass

# --- Standalone test mode ---
if __name__ == "__main__":
    init_gpio()
    start_listener()
    try:
        while True:
            txt = input("Enter message: ")
            send_message(txt)
            time.sleep(0.2)
            print("Last RX:", get_last_message())
    except KeyboardInterrupt:
        cleanup()

import serial
import time
from Config import *

class KeyboardController:
    def __init__(self):
        self.ser = None
        self.connected = False
    
    def connect(self):
        """Connect to the keyboard hardware"""
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            raise Exception(f"Serial connection error: {e}")
    
    def disconnect(self):
        """Disconnect from the keyboard hardware"""
        if self.ser:
            self.ser.close()
            self.connected = False
    
    def send_keys(self, key_brightness_dict, timeout=0.02, max_retries=10):
        """Send key data to serial device"""
        if not key_brightness_dict or not self.connected:
            return False
        
        count = len(key_brightness_dict)
        frame = bytearray([PACKET_START, count])
        for key, val in key_brightness_dict.items():
            frame.append(UPDATE_FLAG)
            frame.append(max(0, min(NUM_KEYS-1, int(key))))
            frame.append(max(0, min(99, int(val))))
        frame.append(PACKET_END)

        for attempt in range(max_retries):
            try:
                self.ser.write(frame)
                self.ser.flush()
                start_time = time.time()
                while True:
                    if self.ser.in_waiting:
                        resp = self.ser.read(1)[0]
                        if resp == READY_FLAG:
                            return True
                        elif resp == ERROR_FLAG:
                            break
                    if time.time() - start_time > timeout:
                        break
                    time.sleep(0.001)
            except Exception:
                break
        return False
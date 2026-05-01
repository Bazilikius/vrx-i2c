#!/usr/bin/env python3
import argparse
import serial
import time
import sys
from vtx_table import BAND_TABLE

def main():
    parser = argparse.ArgumentParser(description='Control VTX and VRX via ESP32')
    parser.add_argument('--port', required=True, help='Serial port of the ESP32 (e.g., /dev/ttyUSB0 or COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--freq', type=int, help='Frequency in MHz to set on both VTX and VRX')
    parser.add_argument('--vtx-freq', type=int, help='Frequency in MHz to set ONLY on VTX')
    parser.add_argument('--vrx-freq', type=int, help='Frequency in MHz to set ONLY on VRX')
    parser.add_argument('--band', help='Band name (e.g., "Band A", "Band R")')
    parser.add_argument('--chan', type=int, help='Channel number (1-8)')
    parser.add_argument('--power', type=int, help='VTX power in mW')
    parser.add_argument('--servo', type=int, help='Set Servo angle (0-180)')
    parser.add_argument('--addr', help='VRX I2C address in hex (e.g., 54)')
    parser.add_argument('--sda', type=int, help='I2C SDA pin')
    parser.add_argument('--scl', type=int, help='I2C SCL pin')
    parser.add_argument('--scan', action='store_true', help='Scan I2C bus for VRX')

    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1)
        time.sleep(2)  # Wait for ESP32 to reset/initialize

        # Clear buffer
        ser.reset_input_buffer()

        if args.sda is not None and args.scl is not None:
            ser.write(f"I {args.sda} {args.scl}\n".encode())
            print(f"Sent: Set I2C pins to SDA:{args.sda}, SCL:{args.scl}")
            time.sleep(0.1)
            print(ser.readline().decode().strip())

        if args.addr:
            ser.write(f"A {args.addr}\n".encode())
            print(f"Sent: Set VRX I2C address to 0x{args.addr}")
            time.sleep(0.1)
            print(ser.readline().decode().strip())

        if args.scan:
            ser.write(b"S\n")
            print("Sent: I2C Scan command")
            # Wait a bit more for scan results
            time.sleep(1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        freq = args.freq
        if args.band and args.chan:
            if args.band in BAND_TABLE:
                if 1 <= args.chan <= 8:
                    freq = BAND_TABLE[args.band][args.chan - 1]
                    print(f"Resolved {args.band} CH{args.chan} to {freq} MHz")
                else:
                    print("Error: Channel must be between 1 and 8")
            else:
                print(f"Error: Unknown Band '{args.band}'")

        if freq:
            ser.write(f"F {freq}\n".encode())
            print(f"Sent: Set BOTH Frequency to {freq} MHz")
            time.sleep(0.1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        if args.servo is not None:
            ser.write(f"X {args.servo}\n".encode())
            print(f"Sent: Set Servo angle to {args.servo}°")
            time.sleep(0.1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        if args.vtx_freq:
            ser.write(f"V {args.vtx_freq}\n".encode())
            print(f"Sent: Set VTX Frequency to {args.vtx_freq} MHz")
            time.sleep(0.1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        if args.vrx_freq:
            ser.write(f"R {args.vrx_freq}\n".encode())
            print(f"Sent: Set VRX Frequency to {args.vrx_freq} MHz")
            time.sleep(0.1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        if args.power:
            ser.write(f"P {args.power}\n".encode())
            print(f"Sent: Set VTX Power to {args.power} mW")
            time.sleep(0.1)
            while ser.in_waiting:
                print(ser.readline().decode().strip())

        ser.close()

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

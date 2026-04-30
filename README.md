# VTX/VRX Controller for ESP32

This project allows you to control a 1.2Ghz/1.3GHz Video Transmitter (VTX) and Video Receiver (VRX) from a PC using an ESP32.

- **VTX:** Rush 1.2/1.3GHz 1.6W (IRC Tramp protocol)
- **VRX:** Controlled via I2C (16-bit little-endian frequency mapping)

## Hardware Connections

### ESP32 to VTX
- **VTX SmartAudio/IRC Pin** -> ESP32 **GPIO 17 (TX2)**
- **GND** -> ESP32 **GND**
- **VTX Power** -> External Power Source (ensure common GND)

### ESP32 to VRX
- **VRX SDA** -> ESP32 **GPIO 21 (SDA)**
- **VRX SCL** -> ESP32 **GPIO 22 (SCL)**
- **GND** -> ESP32 **GND**
- **VRX Power** -> External Power Source (ensure common GND)

## ESP32 Firmware

1. Open `esp32_vtx_vrx_controller/esp32_vtx_vrx_controller.ino` in the Arduino IDE.
2. Select your ESP32 board.
3. Upload the sketch to the ESP32.

## PC Control Script

### Prerequisites

- Python 3.x
- `pyserial` library

Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### CLI Version
Run the script with the following arguments:

```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --freq 1200 --power 1600
```

#### GUI Version
You can also use a graphical interface to control the VTX and VRX:

```bash
python3 vtx_vrx_gui.py
```
This requires `tkinter` to be installed on your system.

#### Arguments:
- `--port`: The serial port of your ESP32 (e.g., `COM3` on Windows, `/dev/ttyUSB0` on Linux).
- `--freq`: Frequency in MHz (e.g., 1080, 1120, 1200, 5865).
- `--power`: VTX output power in mW (e.g., 25, 200, 1600).
- `--addr`: (Optional) Change the VRX I2C address (hex, default: `54`).
- `--scan`: (Optional) Scan the I2C bus to find the VRX address.

### Examples

Set frequency to 1280 MHz and power to 1600 mW:
```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --freq 1280 --power 1600
```

Scan for I2C devices:
```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --scan
```

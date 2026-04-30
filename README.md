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
The graphical interface provides a convenient button-based control system:

```bash
python3 vtx_vrx_gui.py
```

**GUI Layout:**
- **VTX Column**: One-click buttons for standard 1.2GHz frequencies.
- **Power Column**: Buttons for selecting VTX output power (25mW to 1600mW).
- **VRX Grid**: A scrollable list of all bands and channels. Each button shows the Band, Channel, and Frequency.

#### Arguments:
- `--port`: The serial port of your ESP32 (e.g., `COM3` on Windows, `/dev/ttyUSB0` on Linux).
- `--freq`: Frequency in MHz (e.g., 1080, 1120, 1200, 5865).
- `--band`: Band name (e.g., "Band A", "Band R").
- `--chan`: Channel number (1-8).
- `--power`: VTX output power in mW (e.g., 25, 200, 1600).
- `--addr`: (Optional) Change the VRX I2C address (hex, default: `68`).
- `--scan`: (Optional) Scan the I2C bus to find the VRX address.

### Examples

Set frequency to 1280 MHz and power to 1600 mW:
```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --freq 1280 --power 1600
```

Set using Band and Channel:
```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --band "Band R" --chan 1 --power 25
```

Scan for I2C devices:
```bash
python3 vtx_vrx_control.py --port /dev/ttyUSB0 --scan
```

## Troubleshooting ESP32 Upload Errors

If you see `Failed to connect to ESP32: No serial data received` when uploading:

1.  **Manual Bootloader Mode**:
    -   Hold the **BOOT** (or IO0) button on the ESP32.
    -   Press and release the **EN** (or RESET) button.
    -   Release the **BOOT** button.
    -   Try uploading again.
2.  **Check Hardware**:
    -   Ensure you are using a **USB data cable** (some cables are for charging only).
    -   Verify that the correct **COM port** is selected in the Arduino IDE (Tools > Port).
3.  **Drivers**: Install the necessary drivers for your board (usually **CP210x** or **CH340**).
4.  **Upload Speed**: Try reducing the "Upload Speed" in Tools to `115200`.

## Troubleshooting I2C

If the scanner reports **"No I2C devices found"**:

1.  **Check Wiring**: Ensure SDA and SCL are connected to the correct pins on the ESP32.
2.  **Pull-up Resistors**: I2C requires pull-up resistors (typically 4.7kΩ or 10kΩ) on both SDA and SCL lines to 3.3V. Some ESP32 boards or VRX modules might already have them, but others don't.
3.  **Pin Configuration**: If you are not using the default pins (GPIO 21 for SDA, GPIO 22 for SCL), use the `--sda` and `--scl` flags in the CLI or the "Set I2C Pins" button in the GUI to change them at runtime.
4.  **Common Errors**:
    *   `Error: 2`: Address NACK (device not found at this address).
    *   `Error: 3`: Data NACK (communication issue).
    *   `Error: 4`: Other error (often indicates a bus short or missing pull-ups).

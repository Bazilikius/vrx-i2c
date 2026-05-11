# VTX/VRX Controller for ESP32 with LoRa Telemetry

This project allows you to control a 1.2Ghz/1.3GHz Video Transmitter (VTX) and Video Receiver (VRX) from a PC using a pair of ESP32s and Ebyte E32 LoRa modules for long-range remote operation.

- **VTX:** Rush 1.2/1.3GHz 1.6W (IRC Tramp protocol)
- **VRX:** Controlled via I2C (16-bit little-endian frequency mapping)
- **Servo:** Digital Servo control (PWM 50Hz, 360° range)
- **Feedback:** 4x4 Keypad support (Rows: 32, 33, 25, 26; Cols: 27, 14, 15, 5)
- **Power:** MOSFET System Power control
- **Remote:** Long-range transparent bridge via E32 LoRa modules (9600 baud)

## LoRa Architecture

The system consists of two ESP32 nodes:

1.  **Base Node (PC Transmitter):**
    - Connects to the PC via USB.
    - Runs `esp32_lora_bridge/esp32_lora_bridge.ino`.
    - Acts as a transparent gateway between the PC GUI and the LoRa network.
2.  **Remote Node (Hardware Controller):**
    - Connected to the VTX, VRX, and Servo.
    - Runs `esp32_vtx_vrx_controller/esp32_vtx_vrx_controller.ino`.
    - Receives commands over LoRa and sends telemetry back to the Base Node.

## Hardware Connections

### ESP32 to VTX
- **VTX SmartAudio/IRC Pin** -> ESP32 **GPIO 23** (Ensure good connection for bidirectional telemetry)
- **GND** -> ESP32 **GND**
- **VTX Power** -> External Power Source (ensure common GND)

### ESP32 to VRX
- **VRX SDA** -> ESP32 **GPIO 21 (SDA)**
- **VRX SCL** -> ESP32 **GPIO 22 (SCL)**
- **GND** -> ESP32 **GND**
- **VRX Power** -> External Power Source (ensure common GND)

### ESP32 to Servo
- **Servo Signal** -> ESP32 **GPIO 13**
- **GND** -> ESP32 **GND**
- **VCC** -> External 5V Power Source (ensure common GND)

### ESP32 to 4x4 Keypad
- **Rows [1-4]** -> ESP32 **GPIO 32, 33, 25, 26**
- **Cols [1-4]** -> ESP32 **GPIO 27, 14, 15, 5**

### ESP32 to MOSFET
- **MOSFET Gate** -> ESP32 **GPIO 4** (HIGH = ON, LOW = OFF)

### ESP32 to LoRa (E32 Module) - Both Nodes
- **LoRa RX** -> ESP32 **GPIO 17 (TX2)**
- **LoRa TX** -> ESP32 **GPIO 16 (RX2)**
- **M0 / M1** -> GND (for Transparent Mode)
- **VCC / GND** -> 3.3V / GND (Ensure adequate power for LoRa transmission)

### Full Pinout Table (Remote Node)

| Peripheral | ESP32 Pin | Function |
|------------|-----------|----------|
| **VTX (IRC Tramp)** | GPIO 23 | Single wire data (TX/RX) |
| **VRX (I2C SDA)** | GPIO 21 | Data line |
| **VRX (I2C SCL)** | GPIO 22 | Clock line |
| **Digital Servo** | GPIO 13 | PWM Control (360° range) |
| **MOSFET Relay** | GPIO 4 | Power Control (Main System) |
| **Keypad Rows** | 32, 33, 25, 26 | Matrix Scanning |
| **Keypad Cols** | 27, 14, 15, 5 | Matrix Scanning |
| **LoRa (E32)** | GPIO 16, 17 | Serial2 (9600 Baud) |

## MOSFET Relay Setup
The MOSFET relay on **GPIO 4** is used as a master power switch for the VTX and VRX peripherals.
- **Logic HIGH (3.3V)**: Relay closed / Power ON.
- **Logic LOW (0V)**: Relay open / Power OFF.
- **Default State**: The ESP32 firmware defaults to **ON** during setup.

## ESP32 Firmware

1. Open `esp32_vtx_vrx_controller/esp32_vtx_vrx_controller.ino` in the Arduino IDE.
2. Select your ESP32 board.
3. Upload the sketch to the ESP32.

## PC Control Script

### Prerequisites

- Python 3.x
- `pyserial` library
- `tkintermapview` library (for map integration)

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

**Hotkeys:**
- **Left / Right Arrows**: Servo -5° / +5°
- **Numpad 8 / 2**: Servo +5° / -5°
- **Numpad 6 / 4**: Servo +20° / -20°
- **Numpad 5**: Center Servo (180°)
- **Numpad * / /**: Set Servo to 0° / 360°

```bash
python3 vtx_vrx_gui.py
```

**GUI Layout:**
- **Hardware Controls Tab**:
    - **VTX Column**: One-click buttons for standard 1.2GHz frequencies.
    - **Power Column**: Buttons for selecting VTX output power (25mW to 1600mW).
    - **VRX Grid**: A scrollable list of all bands and channels. Each button shows the Band, Channel, and Frequency.
- **Satellite Map Tab**:
    - **Hybrid Map**: View a satellite map with city names and road labels (Google Hybrid).
    - **Marker Placement**: Right-click on the map or enter coordinates to set the system location marker.
    - **Tactical Overlay**: Concentric 5/10/15km white rings and 30° azimuth radials are drawn around the marker.
    - **Servo Needle**: A red needle shows the current 360° servo orientation on the map.
    - **Quick Favorites**: Access your favorite frequencies directly from the map sidebar.
- **Favorites System**:
    - **Add Favorites**: Right-click any frequency button in the Hardware Controls tab to add it to your favorites.
    - **Persistence**: Favorites are saved to `favorites.json` and persist across restarts.

#### Arguments:
- `--port`: The serial port of your ESP32 (e.g., `COM3` on Windows, `/dev/ttyUSB0` on Linux).
- `--freq`: Frequency in MHz (e.g., 1080, 1120, 1200, 5865).
- `--band`: Band name (e.g., "Band A", "Band R").
- `--chan`: Channel number (1-8).
- `--power`: VTX output power in mW (e.g., 25, 200, 1600).
- `--servo`: Set Digital Servo angle (0-360).
- `--mosfet`: Set MOSFET Power (0=OFF, 1=ON).
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

## VTX Troubleshooting (No Power/Channel Change)

If your VTX does not respond to commands:

1. **Verify Pin**: The VTX data wire (IRC Tramp/SmartAudio) must be connected to ESP32 **GPIO 23**.
2. **Check Baud Rate**:
   - Most modern VTXs use **9600** (IRC Tramp).
   - Some use **4800** (SmartAudio). Use the toggle buttons in the PC GUI console to test both.
3. **Common Ground**: Ensure the ESP32 and VTX share a common **GND**.
4. **Logic Levels**: The ESP32 uses 3.3V logic. If your VTX strictly requires 5V logic for data, a logic level shifter may be needed (though 3.3V works for most Rush VTXs).
5. **Debug Console**: Watch the GUI console. It will show the exact HEX bytes being sent to the VTX.
6. **Bidirectional Support**: The system now supports VTX telemetry. Use the "Request VTX Info" button in the GUI to verify if the VTX is communicating back to the ESP32.
7. **LoRa Link Diagnostics**: Use the "📡 Ping Link" button in the GUI to verify the connection.
   - **Link: Base OK**: The PC can talk to the local USB bridge.
   - **Link: REMOTE OK**: The LoRa wireless link to the antenna controller is active.

## Troubleshooting I2C

If the scanner reports **"No I2C devices found"**:

1.  **Check Wiring**: Ensure SDA and SCL are connected to the correct pins on the ESP32.
2.  **Pull-up Resistors**: I2C requires pull-up resistors (typically 4.7kΩ or 10kΩ) on both SDA and SCL lines to 3.3V. Some ESP32 boards or VRX modules might already have them, but others don't.
3.  **Pin Configuration**: If you are not using the default pins (GPIO 21 for SDA, GPIO 22 for SCL), use the `--sda` and `--scl` flags in the CLI or the "Set I2C Pins" button in the GUI to change them at runtime.
4.  **Common Errors**:
    *   `Error: 2`: Address NACK (device not found at this address).
    *   `Error: 3`: Data NACK (communication issue).
    *   `Error: 4`: Other error (often indicates a bus short or missing pull-ups).

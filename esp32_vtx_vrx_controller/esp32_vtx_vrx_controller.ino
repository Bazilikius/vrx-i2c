#include <Wire.h>

// Pin definitions for ESP32
// VTX IRC Tramp uses a single wire, we connect it to TX pin.
#define VTX_SERIAL Serial1
#define VTX_TX_PIN 17
#define VTX_RX_PIN 16

// Default I2C address for VRX (can be changed via command)
uint8_t vrx_i2c_addr = 0x54;

// IRC Tramp packet structure
void sendTrampPacket(char cmd, uint16_t value) {
  uint8_t packet[16];
  memset(packet, 0, 16);

  packet[0] = 15; // Start byte
  packet[1] = cmd;
  packet[2] = value & 0xFF;
  packet[3] = (value >> 8) & 0xFF;

  // Calculate checksum
  uint8_t checksum = 0;
  for (int i = 1; i < 14; i++) {
    checksum += packet[i];
  }
  packet[14] = checksum;
  packet[15] = 0; // End byte

  VTX_SERIAL.write(packet, 16);
}

void setVtxFrequency(uint16_t freq) {
  sendTrampPacket('f', freq);
}

void setVtxPower(uint16_t power) {
  sendTrampPacket('p', power);
}

void setVrxFrequency(uint16_t freq) {
  // According to the table, the frequency is sent as a 16-bit little-endian value.
  // Example: 5865 (0x16E9) -> [0xE9, 0x16]
  uint8_t lowByte = freq & 0xFF;
  uint8_t highByte = (freq >> 8) & 0xFF;

  Wire.beginTransmission(vrx_i2c_addr);
  Wire.write(lowByte);
  Wire.write(highByte);
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.printf("VRX: Set to %d MHz (0x%02X 0x%02X)\n", freq, lowByte, highByte);
  } else {
    Serial.printf("VRX: Error sending to I2C address 0x%02X (Error: %d)\n", vrx_i2c_addr, error);
  }
}

void scanI2C() {
  Serial.println("Scanning I2C bus...");
  byte count = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      Serial.printf("Found I2C device at 0x%02X\n", address);
      count++;
    }
  }
  if (count == 0) Serial.println("No I2C devices found.");
}

void setup() {
  // USB Serial for PC communication
  Serial.begin(115200);

  // VTX Serial (IRC Tramp @ 9600 baud)
  VTX_SERIAL.begin(9600, SERIAL_8N1, VTX_RX_PIN, VTX_TX_PIN);

  // I2C for VRX (Default SDA 21, SCL 22 on ESP32)
  Wire.begin();

  Serial.println("ESP32 VTX/VRX Controller Initialized");
  Serial.println("Commands:");
  Serial.println("  F <freq_mhz> - Set VTX & VRX frequency");
  Serial.println("  P <power_mw> - Set VTX power");
  Serial.println("  A <i2c_addr> - Set VRX I2C address (hex, e.g. A 54)");
  Serial.println("  S            - Scan I2C bus");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() == 0) return;

    char cmd = input.charAt(0);
    String arg = input.substring(1);
    arg.trim();

    if (cmd == 'F') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVtxFrequency(freq);
        setVrxFrequency(freq);
        Serial.printf("Set Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'P') {
      uint16_t power = arg.toInt();
      setVtxPower(power);
      Serial.printf("Set VTX Power: %d mW\n", power);
    } else if (cmd == 'A') {
      // Hex address expected, e.g., "A 54"
      uint8_t addr = (uint8_t) strtol(arg.c_str(), NULL, 16);
      if (addr > 0) {
        vrx_i2c_addr = addr;
        Serial.printf("VRX I2C address set to 0x%02X\n", vrx_i2c_addr);
      }
    } else if (cmd == 'S') {
      scanI2C();
    } else {
      Serial.println("Unknown command.");
    }
  }
}

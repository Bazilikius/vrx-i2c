#include <Wire.h>

// Pin definitions for ESP32
// VTX IRC Tramp uses a single wire, we connect it to TX pin.
#define VTX_SERIAL Serial1
#define VTX_TX_PIN 17
#define VTX_RX_PIN 16

// Default I2C configuration
int i2c_sda_pin = 21;
int i2c_scl_pin = 22;

// Default I2C address for VRX (can be changed via command)
// User provided: 8 bit - 0xD0, 7 bit - 0x68
uint8_t vrx_i2c_addr = 0x68;

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
  // Send 3 times for reliability
  for (int i = 0; i < 3; i++) {
    sendTrampPacket('f', freq);
    delay(50);
  }
}

void setVtxPower(uint16_t power) {
  // Send 3 times for reliability
  for (int i = 0; i < 3; i++) {
    sendTrampPacket('p', power);
    delay(50);
  }
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
  Serial.printf("Scanning I2C bus (SDA:%d, SCL:%d)...\n", i2c_sda_pin, i2c_scl_pin);
  byte count = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    byte error = Wire.endTransmission();
    if (error == 0) {
      Serial.printf("Found I2C device at 0x%02X\n", address);
      count++;
    } else if (error == 4) {
      Serial.printf("Unknown error at address 0x%02X\n", address);
    }
  }
  if (count == 0) {
    Serial.println("No I2C devices found. Check your wiring and pull-up resistors.");
  } else {
    Serial.printf("Scan complete. Found %d device(s).\n", count);
  }
}

void setup() {
  // USB Serial for PC communication
  Serial.begin(115200);

  // VTX Serial (IRC Tramp @ 9600 baud)
  VTX_SERIAL.begin(9600, SERIAL_8N1, VTX_RX_PIN, VTX_TX_PIN);

  // I2C for VRX
  Wire.begin(i2c_sda_pin, i2c_scl_pin);

  Serial.println("ESP32 VTX/VRX Controller Initialized");
  Serial.println("Commands:");
  Serial.println("  V <freq_mhz> - Set ONLY VTX frequency");
  Serial.println("  R <freq_mhz> - Set ONLY VRX frequency");
  Serial.println("  F <freq_mhz> - Set BOTH VTX & VRX frequency");
  Serial.println("  P <power_mw> - Set VTX power");
  Serial.println("  A <i2c_addr> - Set VRX I2C address (hex, e.g. A 68)");
  Serial.println("  I <sda> <scl>- Set I2C pins");
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

    if (cmd == 'V') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVtxFrequency(freq);
        Serial.printf("Set VTX Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'R') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVrxFrequency(freq);
        Serial.printf("Set VRX Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'F') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVtxFrequency(freq);
        setVrxFrequency(freq);
        Serial.printf("Set BOTH Frequency: %d MHz\n", freq);
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
    } else if (cmd == 'I') {
      int firstSpace = arg.indexOf(' ');
      if (firstSpace != -1) {
        int sda = arg.substring(0, firstSpace).toInt();
        int scl = arg.substring(firstSpace + 1).toInt();
        i2c_sda_pin = sda;
        i2c_scl_pin = scl;
        Wire.end();
        Wire.begin(i2c_sda_pin, i2c_scl_pin);
        Serial.printf("I2C pins set to SDA:%d, SCL:%d\n", i2c_sda_pin, i2c_scl_pin);
      }
    } else if (cmd == 'S') {
      scanI2C();
    } else {
      Serial.println("Unknown command.");
    }
  }
}

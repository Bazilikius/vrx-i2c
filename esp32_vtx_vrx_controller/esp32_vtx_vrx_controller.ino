#include <Wire.h>
#include <Preferences.h>

// Persistent Storage
Preferences prefs;

// Pin definitions for ESP32
// VTX IRC Tramp / SmartAudio uses a single wire, connect to TX pin.
// Moved to GPIO 23 to avoid conflicts with Serial2 RX on some boards.
#define VTX_SERIAL Serial1
#define VTX_TX_PIN 23
#define VTX_RX_PIN 34 // Use 34 (input-only, safe for dummy RX)

// LoRa Configuration (E32)
#define LORA_SERIAL Serial2
#define LORA_RX_PIN 16
#define LORA_TX_PIN 17
#define LORA_BAUD 9600

// Default I2C configuration
int i2c_sda_pin = 21;
int i2c_scl_pin = 22;

// Servo Configuration (360 Degree)
int servo_pin = 13;
const int servo_freq = 50;
volatile int current_servo_angle = 180; // Default to center of 360

// Power Pins
const int mosfet_pin = 4;

// Keypad Configuration (4x4 Matrix)
const int ROW_PINS[4] = {32, 33, 25, 26};
// Moved col from 4 to 15
const int COL_PINS[4] = {27, 14, 15, 5};
char keys[4][4] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
unsigned long last_key_time = 0;
const int debounce_ms = 300;

// Default I2C address for VRX (can be changed via command)
// User provided: 8 bit - 0xD0, 7 bit - 0x68
uint8_t vrx_i2c_addr = 0x68;

void sendFeedback(const char* format, ...) {
  char buffer[128];
  va_list args;
  va_start(args, format);
  vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);

  // Send to both USB and LoRa
  Serial.print(buffer);
  LORA_SERIAL.print(buffer);
}

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
  VTX_SERIAL.flush(); // Ensure data is sent

  // Debug output
  Serial.printf("VTX SEND [%c:%d]: ", cmd, value);
  for(int i=0; i<16; i++) Serial.printf("%02X ", packet[i]);
  Serial.println();
}

void setVtxFrequency(uint16_t freq) {
  for (int i = 0; i < 3; i++) {
    sendTrampPacket('F', freq);
    delay(50);
  }
}

void setVtxPower(uint16_t power) {
  for (int i = 0; i < 3; i++) {
    sendTrampPacket('P', power);
    delay(50);
  }
}

void requestVtxConfig() {
  // Request VTX config with 'v' command
  sendTrampPacket('v', 0);

  // Wait for response (16 bytes)
  unsigned long start = millis();
  while (VTX_SERIAL.available() < 16 && millis() - start < 500) {
    delay(10);
  }

  if (VTX_SERIAL.available() >= 16) {
    uint8_t buffer[16];
    VTX_SERIAL.readBytes(buffer, 16);

    // Simple report to PC
    sendFeedback("VTX_INFO: ");
    for(int i=0; i<16; i++) {
        char hex_buf[4];
        sprintf(hex_buf, "%02X ", buffer[i]);
        sendFeedback(hex_buf);
    }
    sendFeedback("\n");

    // Parse if it looks like a valid Tramp response (Sync 0x0F)
    if (buffer[0] == 0x0F) {
       uint16_t f = buffer[2] | (buffer[3] << 8);
       uint16_t p = buffer[4] | (buffer[5] << 8);
       sendFeedback("VTX_STATUS: Freq=%d, Pwr=%d\n", f, p);
    }
  } else {
    sendFeedback("VTX_INFO: No response\n");
  }
}

void setVrxFrequency(uint16_t freq) {
  uint8_t lowByte = freq & 0xFF;
  uint8_t highByte = (freq >> 8) & 0xFF;

  // Attempt to recover I2C bus if it's stuck
  if (digitalRead(i2c_sda_pin) == LOW || digitalRead(i2c_scl_pin) == LOW) {
    Wire.end();
    Wire.begin(i2c_sda_pin, i2c_scl_pin, 100000);
  }

  Wire.beginTransmission(vrx_i2c_addr);
  Wire.write(lowByte);
  Wire.write(highByte);
  byte error = Wire.endTransmission();

  if (error == 0) {
    sendFeedback("VRX: Set to %d MHz (0x%02X 0x%02X)\n", freq, lowByte, highByte);
  } else {
    // Retry once on error 4
    if (error == 4) {
       delay(10);
       Wire.beginTransmission(vrx_i2c_addr);
       Wire.write(lowByte);
       Wire.write(highByte);
       error = Wire.endTransmission();
    }

    if (error == 0) {
      sendFeedback("VRX: Set to %d MHz (Success after retry)\n", freq);
    } else {
      sendFeedback("VRX: Error sending to I2C address 0x%02X (Error: %d)\n", vrx_i2c_addr, error);
    }
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

void setServoAngle(int angle) {
  if (angle < 0) angle = 0;
  if (angle > 360) angle = 360;

  current_servo_angle = angle;

  // Mapping 0-360 to 500us-2500us
  uint32_t duty = map(angle, 0, 360, 205, 1024);
  ledcWrite(servo_pin, duty);

  // Feedback for PC GUI
  sendFeedback("A: %d\n", current_servo_angle);
}


void checkKeypad() {
  if (millis() - last_key_time < debounce_ms) return;

  for (int c = 0; c < 4; c++) {
    // Columns as outputs
    pinMode(COL_PINS[c], OUTPUT);
    digitalWrite(COL_PINS[c], LOW);

    for (int r = 0; r < 4; r++) {
      if (digitalRead(ROW_PINS[r]) == LOW) {
        char key = keys[r][c];
        Serial.printf("Keypad: Pressed %c\n", key);
        processKey(key);
        last_key_time = millis();
      }
    }
    digitalWrite(COL_PINS[c], HIGH);
    pinMode(COL_PINS[c], INPUT_PULLUP);
  }
}

void processKey(char key) {
  if (key == '8') setServoAngle(current_servo_angle + 5);
  else if (key == '2') setServoAngle(current_servo_angle - 5);
  else if (key == '4') setServoAngle(current_servo_angle - 20);
  else if (key == '6') setServoAngle(current_servo_angle + 20);
  else if (key == '5') setServoAngle(135); // Center of 270
  else if (key == '*') setServoAngle(0);
  else if (key == '#') setServoAngle(270);
}

void setup() {
  // USB Serial for local debug
  Serial.begin(115200);

  // LoRa Serial for remote PC control
  LORA_SERIAL.begin(LORA_BAUD, SERIAL_8N1, LORA_RX_PIN, LORA_TX_PIN);

  // VTX Serial
  VTX_SERIAL.begin(9600, SERIAL_8N1, VTX_RX_PIN, VTX_TX_PIN);

  // I2C for VRX (100kHz for stability)
  Wire.begin(i2c_sda_pin, i2c_scl_pin, 100000);
  Wire.setTimeOut(100); // 100ms timeout

  // Servo Setup
  ledcAttach(servo_pin, servo_freq, 13);
  setServoAngle(180); // Default to center of 360

  // Power Setup
  pinMode(mosfet_pin, OUTPUT);
  digitalWrite(mosfet_pin, HIGH);

  // Keypad Setup
  for (int i = 0; i < 4; i++) {
    pinMode(ROW_PINS[i], INPUT_PULLUP);
    pinMode(COL_PINS[i], INPUT_PULLUP);
  }

  // Load Saved Settings
  prefs.begin("vtxvrx", false);
  uint16_t saved_vtx_f = prefs.getUInt("vtx_f", 1200);
  uint16_t saved_vrx_f = prefs.getUInt("vrx_f", 5865);
  uint16_t saved_vtx_p = prefs.getUInt("vtx_p", 25);
  int saved_servo_a = prefs.getInt("servo_a", 180);

  // Apply Saved Settings
  setVtxFrequency(saved_vtx_f);
  setVrxFrequency(saved_vrx_f);
  setVtxPower(saved_vtx_p);
  setServoAngle(saved_servo_a);

  Serial.println("ESP32 VTX/VRX/Servo/Keypad Controller Initialized");
  Serial.println("Commands:");
  Serial.println("  V <freq_mhz> - Set ONLY VTX frequency");
  Serial.println("  R <freq_mhz> - Set ONLY VRX frequency");
  Serial.println("  B <baud>     - Change VTX baud (9600=Tramp, 4800=SmartAudio)");
  Serial.println("  Q            - Request VTX Configuration (Telemetry)");
  Serial.println("  F <freq_mhz> - Set BOTH VTX & VRX frequency");
  Serial.println("  P <power_mw> - Set VTX power");
  Serial.println("  X <angle>    - Set Servo angle (0-270)");
  Serial.println("  A <i2c_addr> - Set VRX I2C address (hex, e.g. A 68)");
  Serial.println("  I <sda> <scl>- Set I2C pins");
  Serial.println("  J <pin>      - Set Servo pin");
  Serial.println("  S            - Scan I2C bus");
}

void handleCommand(String input) {
    input.trim();
    if (input.length() == 0) return;

    char cmd = input.charAt(0);
    String arg = input.substring(1);
    arg.trim();

    if (cmd == 'V') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVtxFrequency(freq);
        prefs.putUInt("vtx_f", freq);
        sendFeedback("Set VTX Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'B') {
      int baud = arg.toInt();
      if (baud == 4800 || baud == 9600) {
        VTX_SERIAL.end();
        VTX_SERIAL.begin(baud, SERIAL_8N1, VTX_RX_PIN, VTX_TX_PIN);
        sendFeedback("VTX Baud set to %d\n", baud);
      }
    } else if (cmd == 'R') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVrxFrequency(freq);
        prefs.putUInt("vrx_f", freq);
        sendFeedback("Set VRX Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'F') {
      uint16_t freq = arg.toInt();
      if (freq > 0) {
        setVtxFrequency(freq);
        setVrxFrequency(freq);
        prefs.putUInt("vtx_f", freq);
        prefs.putUInt("vrx_f", freq);
        sendFeedback("Set BOTH Frequency: %d MHz\n", freq);
      }
    } else if (cmd == 'P') {
      uint16_t power = arg.toInt();
      setVtxPower(power);
      prefs.putUInt("vtx_p", power);
      sendFeedback("Set VTX Power: %d mW\n", power);
    } else if (cmd == 'A') {
      // Hex address expected, e.g., "A 54"
      uint8_t addr = (uint8_t) strtol(arg.c_str(), NULL, 16);
      if (addr > 0) {
        vrx_i2c_addr = addr;
        sendFeedback("VRX I2C address set to 0x%02X\n", vrx_i2c_addr);
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
        sendFeedback("I2C pins set to SDA:%d, SCL:%d\n", i2c_sda_pin, i2c_scl_pin);
      }
    } else if (cmd == 'X') {
      int angle = arg.toInt();
      setServoAngle(angle);
      prefs.putInt("servo_a", angle);
    } else if (cmd == 'J') {
      int pin = arg.toInt();
      if (pin >= 0) {
        ledcDetach(servo_pin);
        servo_pin = pin;
        ledcAttach(servo_pin, servo_freq, 13);
        sendFeedback("Servo pin set to %d\n", servo_pin);
      }
    } else if (cmd == 'M') {
      int state = arg.toInt();
      digitalWrite(mosfet_pin, state == 1 ? HIGH : LOW);
      sendFeedback("System Power: %s\n", state == 1 ? "ON" : "OFF");
    } else if (cmd == 'S') {
      scanI2C();
    } else if (cmd == 'Q') {
      requestVtxConfig();
    } else {
      sendFeedback("Unknown command.\n");
    }
}

void loop() {
  checkKeypad();

  // Handle local USB commands
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    handleCommand(input);
  }

  // Handle remote LoRa commands
  if (LORA_SERIAL.available() > 0) {
    String input = LORA_SERIAL.readStringUntil('\n');
    handleCommand(input);
  }
}

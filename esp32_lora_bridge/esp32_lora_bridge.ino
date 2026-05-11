// ESP32 LoRa Transparent Bridge (Base Node)
// This code acts as a bridge between the PC (USB Serial) and the LoRa module (Serial2).
// PC <-> ESP32 (USB) <-> Serial2 (LoRa) <-> [Air] <-> Remote ESP32

#define LORA_SERIAL Serial2
#define LORA_RX_PIN 16
#define LORA_TX_PIN 17
#define LORA_BAUD 9600
#define PC_BAUD 115200

void setup() {
  // PC USB Serial
  Serial.begin(PC_BAUD);

  // LoRa Module Serial
  LORA_SERIAL.begin(LORA_BAUD, SERIAL_8N1, LORA_RX_PIN, LORA_TX_PIN);

  Serial.println("ESP32 LoRa Bridge Initialized");
  Serial.printf("PC Baud: %d, LoRa Baud: %d\n", PC_BAUD, LORA_BAUD);
}

void loop() {
  // Check for Local Diagnostic commands
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "Z") {
      Serial.println("PONG: BASE OK");
    } else {
      // Forward everything else to LoRa
      LORA_SERIAL.println(input);
    }
  }

  // Forward data from LoRa to PC
  if (LORA_SERIAL.available()) {
    while (LORA_SERIAL.available()) {
      Serial.write(LORA_SERIAL.read());
    }
  }
}

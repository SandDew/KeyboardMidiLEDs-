#include <Adafruit_NeoPixel.h>

#define LED_PIN 11
#define LED_COUNT 123
#define BRIGHTNESS 70

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

const uint8_t keyPattern[12] = {0,1,0,1,0,0,1,0,1,0,1,0};
const uint8_t singleLEDKeys[] = {17, 11, 36};
const uint8_t singleLEDKeyCount = sizeof(singleLEDKeys) / sizeof(singleLEDKeys[0]);

bool isSingleLEDKey(int key) {
  for (uint8_t i = 0; i < singleLEDKeyCount; i++) {
    if (singleLEDKeys[i] == key) return true;
  }
  return false;
}

float keyBrightness[72] = {0}; // 0-99 for each key

#define PACKET_START 0xAA
#define PACKET_END   0x55
#define UPDATE_FLAG  0x01
#define READY_FLAG   0xCC
#define ERROR_FLAG   0xEE

void setup() {
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  strip.show();
  Serial.begin(2000000);
  while (Serial.available()) Serial.read();
}

void loop() {
  if (Serial.available() >= 4) {
    if (Serial.peek() == PACKET_START) {
      if (Serial.available() < 2) return; // Wait for N
      Serial.read(); // consume PACKET_START
      uint8_t count = Serial.read();
      if (count == 0 || count > 72) {
        while (Serial.available()) Serial.read();
        Serial.write(ERROR_FLAG);
        return;
      }
      if (Serial.available() < count * 3 + 1) return; // Wait for full packet
      bool valid = true;
      for (uint8_t i = 0; i < count; i++) {
        uint8_t flag = Serial.read();
        uint8_t key = Serial.read();
        uint8_t val = Serial.read();
        if (flag != UPDATE_FLAG || key >= 72 || val > 99) {
          valid = false;
        } else {
          keyBrightness[key] = val;
        }
      }
      uint8_t end = Serial.read();
      if (valid && end == PACKET_END) {
        Serial.write(READY_FLAG);
      } else {
        while (Serial.available()) Serial.read();
        Serial.write(ERROR_FLAG);
      }
    } else {
      Serial.read();
    }
  }

  // Render all keys (unchanged)
  int led = 4;
  int key = 0;
  int whiteKeyCount = 0;
  while (led < LED_COUNT && key < 72) {
    int ledsForThisKey = isSingleLEDKey(key) ? 1 : 2;
    float brightness = keyBrightness[key] / 99.0 * BRIGHTNESS;
    uint8_t noteInOctave = key % 12;
    uint32_t color = 0;

    if (keyPattern[noteInOctave] == 0) {
      color = (whiteKeyCount % 2 == 0) ? strip.Color(0, brightness, 0) : strip.Color(brightness, brightness, 0);
      whiteKeyCount++;
    } else {
      color = strip.Color(brightness, 0, 0);
    }

    for (int j = 0; j < ledsForThisKey && (led + j) < LED_COUNT; j++) {
      strip.setPixelColor(led + j, color);
    }
    led += ledsForThisKey;
    key++;
  }

  for (; led < LED_COUNT; led++) {
    strip.setPixelColor(led, 0);
  }

  strip.show();
  delay(5);
}


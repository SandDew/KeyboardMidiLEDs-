#include <Adafruit_NeoPixel.h>

#define LED_PIN 11
#define LED_COUNT 123
#define BRIGHTNESS 70
#define LED_TIMEOUT_MS 200  // Turn off LEDs after 200ms of no updates

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

const uint8_t keyPattern[12] = {0,1,0,1,0,0,1,0,1,0,1,0};

// LED configuration: stores which keys use 3 LEDs (bit array)
// 72 keys / 8 bits per byte = 9 bytes
uint8_t threeLEDKeys[9] = {0};

bool isThreeLEDKey(int key) {
  if (key < 0 || key >= 72) return false;
  uint8_t byteIndex = key / 8;
  uint8_t bitIndex = key % 8;
  return (threeLEDKeys[byteIndex] & (1 << bitIndex)) != 0;
}

void setThreeLEDKey(int key, bool enabled) {
  if (key < 0 || key >= 72) return;
  uint8_t byteIndex = key / 8;
  uint8_t bitIndex = key % 8;
  if (enabled) {
    threeLEDKeys[byteIndex] |= (1 << bitIndex);
  } else {
    threeLEDKeys[byteIndex] &= ~(1 << bitIndex);
  }
}

float keyBrightness[72] = {0}; // 0-99 for each key
unsigned long keyLastUpdate[72] = {0}; // Last update time for each key
unsigned long lastClearTime = 0; // Track when we last cleared all keys

#define PACKET_START 0xAA
#define PACKET_END   0x55
#define UPDATE_FLAG  0x01
#define READY_FLAG   0xCC
#define ERROR_FLAG   0xEE
#define CLEAR_FLAG   0x02  // clear all LEDs
#define CONFIG_FLAG  0x03  // configure LED mapping

void setup() {
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  strip.show();
  Serial.begin(2000000);
  while (Serial.available()) Serial.read();
}

void clearAllKeys() {
  for (int i = 0; i < 72; i++) {
    keyBrightness[i] = 0;
    keyLastUpdate[i] = millis(); // Reset timeout counters
  }
  for (int i = 0; i < LED_COUNT; i++) strip.setPixelColor(i, 0);
  strip.show();
  lastClearTime = millis();
}

void checkAndTimeoutKeys() {
  unsigned long currentTime = millis();
  bool anyChanged = false;
  
  // Don't timeout keys immediately after a clear command
  if (currentTime - lastClearTime < LED_TIMEOUT_MS) {
    return;
  }
  
  for (int i = 0; i < 72; i++) {
    // Only check keys that are currently on
    if (keyBrightness[i] > 0) {
      // Check if this key hasn't been updated recently
      if (currentTime - keyLastUpdate[i] > LED_TIMEOUT_MS) {
        keyBrightness[i] = 0;
        anyChanged = true;
      }
    }
  }
  
  // Only update strip if something actually changed
  if (anyChanged) {
    renderLEDs();
  }
}

void renderLEDs() {
  int led = 4;
  int key = 0;
  int whiteKeyCount = 0;
  
  while (led < LED_COUNT && key < 72) {
    // Check if this key uses 3 LEDs, otherwise use 2
    int ledsForThisKey = isThreeLEDKey(key) ? 3 : 2;
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
}

void loop() {
  // Check for timed-out keys first
  checkAndTimeoutKeys();
  
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
      bool sawClear = false;
      unsigned long currentTime = millis();
      
      for (uint8_t i = 0; i < count; i++) {
        uint8_t flag = Serial.read();
        uint8_t key = Serial.read();
        uint8_t val = Serial.read();
        if (flag == UPDATE_FLAG) {
          if (key >= 72 || val > 99) {
            valid = false;
          } else {
            keyBrightness[key] = val;
            keyLastUpdate[key] = currentTime; // Update timestamp
          }
        } else if (flag == CLEAR_FLAG && count == 1) {
          sawClear = true;
          clearAllKeys();
        } else if (flag == CONFIG_FLAG && count == 9) {
          // Receive 9 bytes of LED configuration
          // Each triplet: CONFIG_FLAG, byte_index, byte_value
          if (key < 9) {
            threeLEDKeys[key] = val;
          }
        } else {
          valid = false;
        }
      }
      uint8_t end = Serial.read();
      if (valid && end == PACKET_END) {
        Serial.write(READY_FLAG);
        // Only render if we didn't already clear
        if (!sawClear) {
          renderLEDs();
        }
      } else {
        while (Serial.available()) Serial.read();
        Serial.write(ERROR_FLAG);
      }
    } else {
      Serial.read();
    }
  } else {
    // When no serial data, just do a small delay
    delay(5);
  }
}


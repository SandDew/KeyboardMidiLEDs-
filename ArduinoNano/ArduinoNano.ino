#include <Adafruit_NeoPixel.h>

#define LED_PIN 11
#define LED_COUNT 123
#define BRIGHTNESS 70
#define LED_TIMEOUT_MS 200  // Turn off LEDs after 200ms of no updates

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

const uint8_t keyPattern[12] = {0,1,0,1,0,0,1,0,1,0,1,0};

// LED configuration: stores LED count for each key (1, 2, or 3 LEDs)
// Uses 2 bits per key: 00=2 LEDs (default), 01=1 LED, 10=3 LEDs
// 72 keys * 2 bits = 144 bits = 18 bytes
uint8_t ledCountConfig[18] = {0};

uint8_t getLEDCount(int key) {
  if (key < 0 || key >= 72) return 2;
  uint8_t byteIndex = (key * 2) / 8;
  uint8_t bitOffset = (key * 2) % 8;
  uint8_t value = (ledCountConfig[byteIndex] >> bitOffset) & 0x03;
  // 00 = 2 LEDs (default), 01 = 1 LED, 10 = 3 LEDs
  if (value == 1) return 1;
  if (value == 2) return 3;
  return 2;
}

void setLEDCount(int key, uint8_t count) {
  if (key < 0 || key >= 72) return;
  if (count < 1 || count > 3) return;
  
  uint8_t byteIndex = (key * 2) / 8;
  uint8_t bitOffset = (key * 2) % 8;
  
  // Convert count to 2-bit value: 1->01, 2->00, 3->10
  uint8_t value;
  if (count == 1) value = 1;
  else if (count == 3) value = 2;
  else value = 0;
  
  // Clear the 2 bits and set new value
  uint8_t mask = ~(0x03 << bitOffset);
  ledCountConfig[byteIndex] = (ledCountConfig[byteIndex] & mask) | (value << bitOffset);
}

void cycleLEDCount(int key) {
  uint8_t current = getLEDCount(key);
  uint8_t next = (current == 3) ? 1 : current + 1;
  setLEDCount(key, next);
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
#define CONFIG_MODE_ENTER 0x04  // enter configuration mode (turn on all LEDs)
#define CONFIG_MODE_EXIT  0x05  // exit configuration mode
#define CONFIG_MODE_TOGGLE 0x06 // toggle 3-LED status for a key

bool configurationMode = false;  // Track if we're in configuration mode

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

void enterConfigurationMode() {
  configurationMode = true;
  // Turn on all LEDs at full brightness to visualize mapping
  for (int i = 0; i < 72; i++) {
    keyBrightness[i] = 99; // Full brightness
    keyLastUpdate[i] = millis();
  }
  renderLEDs();
}

void exitConfigurationMode() {
  configurationMode = false;
  clearAllKeys();
}

void checkAndTimeoutKeys() {
  // Don't timeout keys in configuration mode
  if (configurationMode) {
    return;
  }
  
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
    // Get LED count for this key (1, 2, or 3)
    int ledsForThisKey = getLEDCount(key);
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
        } else if (flag == CONFIG_FLAG && count == 18) {
          // Receive 18 bytes of LED configuration (2 bits per key)
          // Each triplet: CONFIG_FLAG, byte_index, byte_value
          if (key < 18) {
            ledCountConfig[key] = val;
          }
        } else if (flag == CONFIG_MODE_ENTER && count == 1) {
          enterConfigurationMode();
        } else if (flag == CONFIG_MODE_EXIT && count == 1) {
          exitConfigurationMode();
        } else if (flag == CONFIG_MODE_TOGGLE && count == 1) {
          // Cycle LED count for a key in config mode (1 -> 2 -> 3 -> 1)
          if (key < 72) {
            cycleLEDCount(key);
            // Re-render to show the change
            renderLEDs();
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


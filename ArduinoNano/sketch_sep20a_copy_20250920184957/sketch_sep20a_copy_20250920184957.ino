#include <Adafruit_NeoPixel.h>

#define LED_PIN 11
#define LED_COUNT 123
#define BRIGHTNESS 70

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

const uint8_t keyPattern[12] = {0,1,0,1,0,0,1,0,1,0,1,0};

// Dynamic LED configuration arrays
uint8_t singleLEDKeys[20] = {17, 11, 36};  // Default values, can be updated
uint8_t singleLEDKeyCount = 3;
uint8_t tripleLEDKeys[20];  // Keys that use 3 LEDs
uint8_t tripleLEDKeyCount = 0;

bool isSingleLEDKey(int key) {
  for (uint8_t i = 0; i < singleLEDKeyCount; i++) {
    if (singleLEDKeys[i] == key) return true;
  }
  return false;
}

bool isTripleLEDKey(int key) {
  for (uint8_t i = 0; i < tripleLEDKeyCount; i++) {
    if (tripleLEDKeys[i] == key) return true;
  }
  return false;
}

int getLedsForKey(int key) {
  if (isSingleLEDKey(key)) return 1;
  if (isTripleLEDKey(key)) return 3;
  return 2;  // Default
}

float keyBrightness[72] = {0}; // 0-99 for each key

#define PACKET_START 0xAA
#define PACKET_END   0x55
#define UPDATE_FLAG  0x01
#define READY_FLAG   0xCC
#define ERROR_FLAG   0xEE
#define CLEAR_FLAG   0x02  // Clear all LEDs
#define CONFIG_FLAG  0x03  // Configuration command

void setup() {
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  strip.show();
  Serial.begin(2000000);
  while (Serial.available()) Serial.read();
}

void clearAllKeys() {
  for (int i = 0; i < 72; i++) keyBrightness[i] = 0;
  for (int i = 0; i < LED_COUNT; i++) strip.setPixelColor(i, 0);
  strip.show();
}

void loop() {
  if (Serial.available() >= 4) {
    if (Serial.peek() == PACKET_START) {
      Serial.read(); // consume PACKET_START
      uint8_t flag = Serial.read();
      
      // Handle configuration packet
      if (flag == CONFIG_FLAG) {
        if (Serial.available() < 2) return; // Wait for data
        uint8_t numSingle = Serial.read();
        
        // Wait for all single LED keys
        if (Serial.available() < numSingle + 1) return;
        
        // Read single LED keys
        singleLEDKeyCount = min(numSingle, (uint8_t)20);
        for (uint8_t i = 0; i < singleLEDKeyCount; i++) {
          singleLEDKeys[i] = Serial.read();
        }
        // Discard extra if more than 20
        for (uint8_t i = singleLEDKeyCount; i < numSingle; i++) {
          Serial.read();
        }
        
        if (Serial.available() < 1) return; // Wait for triple count
        uint8_t numTriple = Serial.read();
        
        // Wait for all triple LED keys + end byte
        if (Serial.available() < numTriple + 1) return;
        
        // Read triple LED keys
        tripleLEDKeyCount = min(numTriple, (uint8_t)20);
        for (uint8_t i = 0; i < tripleLEDKeyCount; i++) {
          tripleLEDKeys[i] = Serial.read();
        }
        // Discard extra if more than 20
        for (uint8_t i = tripleLEDKeyCount; i < numTriple; i++) {
          Serial.read();
        }
        
        uint8_t end = Serial.read();
        if (end == PACKET_END) {
          Serial.write(READY_FLAG);
        } else {
          while (Serial.available()) Serial.read();
          Serial.write(ERROR_FLAG);
        }
        return;
      }
      
      // Handle regular update/clear packets
      uint8_t count = flag;
      if (count == 0 || count > 72) {
        while (Serial.available()) Serial.read();
        Serial.write(ERROR_FLAG);
        return;
      }
      if (Serial.available() < count * 3 + 1) return; // Wait for full packet
      bool valid = true;
      bool sawClear = false;
      for (uint8_t i = 0; i < count; i++) {
        uint8_t pktFlag = Serial.read();
        uint8_t key = Serial.read();
        uint8_t val = Serial.read();
        if (pktFlag == UPDATE_FLAG) {
          if (key >= 72 || val > 99) {
            valid = false;
          } else {
            keyBrightness[key] = val;
          }
        } else if (pktFlag == CLEAR_FLAG && count == 1) {
          sawClear = true;
          clearAllKeys();
        } else {
          valid = false;
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

  // Render LEDs
  int led = 4;
  int key = 0;
  int whiteKeyCount = 0;
  while (led < LED_COUNT && key < 72) {
    int ledsForThisKey = getLedsForKey(key);
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


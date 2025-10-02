# .cursorrules Auto-Generation

SmartDoc automatically creates `.cursorrules` in your project root on first initialization.

## Two Rule Sets

### 1. Core SmartDoc Integration (~875 tokens)

**Purpose:** Teaches Cursor AI to use SmartDoc for documentation queries.

**Behavior:**
- Check SmartDoc before using general knowledge
- Auto-reprocess schematics when confidence < 0.6
- Cite sources from indexed documentation
- Provide SmartDoc commands for indexing/querying

**Always Active:** Essential for SmartDoc functionality.

---

### 2. Hardware Development Rules (~950 tokens, Optional)

**Purpose:** Prevents LLMs from providing generic embedded code without board-specific files.

**Behavior:**
- Detects hardware requests (SPI, I2C, GPIO, HAL, etc.)
- **Requests board files before coding** (pins_arduino.h, HAL drivers, etc.)
- Suggests specific file paths (Arduino IDE, PlatformIO on macOS)
- Provides `find` commands to locate files
- Offers SmartDoc indexing of board packages

**Easily Removable:** Delete section between `# ====` comment blocks if not needed.

---

## Hardware Rules Examples

**Arduino Nano R4:**
```
Files at: ~/.arduino15/packages/arduino/hardware/renesas_uno/1.x.x/
Find: find ~/.arduino15 -path "*renesas_uno*" -name "SPI.h"
```

**ESP32:**
```
Files at: ~/.arduino15/packages/esp32/hardware/esp32/2.x.x/
Find: find ~/.arduino15 -path "*esp32*" -name "pins_arduino.h"
```

**PlatformIO:**
```
Files at: ~/.platformio/packages/framework-arduino[platform]/
Find: find ~/.platformio -name "SPI.h"
```

---

## When to Remove Hardware Rules

Delete if you:
- Don't do embedded/Arduino development
- Want minimal token usage
- Use different development environment (Windows, Linux)

**How:** Open generated `.cursorrules`, delete lines between `# ============================================================================` markers.

---

## Total Token Count

- **Core only:** ~875 tokens
- **Core + Hardware:** ~1,825 tokens

Both sets designed for **macOS** development environments.


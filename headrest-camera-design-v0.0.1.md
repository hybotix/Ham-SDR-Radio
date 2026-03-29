# Headrest Pan/Tilt Camera System
## Product Concept Design Document

**Project:**   Headrest Pan/Tilt Camera System  
**Author:**    Dale — Hybrid RobotiX / The Accessibility Files  
**Tagline:**   "I investigate the inaccessible"  
**Version:**   0.0.1 (Concept)  
**Status:**    Pre-development — Concept Phase  

---

## 1. Overview

A wireless rear-facing pan/tilt camera system designed specifically for power
wheelchair users and other disabled individuals who need rearward situational
awareness without turning their head or body.

The system consists of two fully independent, battery-operated wireless units
with no cables between them:

- **Camera Unit** — mounts to the wheelchair headrest, provides a pan/tilt
  camera with wide-angle rear view
- **Display Unit** — mounts wherever convenient for the user (armrest, tray
  table, etc.), shows the camera feed on a 5" color display

Designed by a wheelchair user, for wheelchair users.

---

## 2. Problem Statement

Power wheelchair users have severely limited rearward visibility. Turning to
look behind is difficult or impossible for many users. This creates real safety
hazards in:

- Reversing in tight spaces
- Navigating crowded environments
- Detecting approaching people or vehicles from behind
- Parking and positioning

Existing solutions (mirrors, phone mounts) are inadequate — mirrors require
the user to look away from their path, and phones require manual operation.

This system provides always-on, hands-free rearward awareness.

---

## 3. Design Philosophy

- **Wireless** — no cables between camera and display units
- **Battery operated** — both units independent, no wiring into the wheelchair
- **Affordable** — target price accessible to disabled users on fixed incomes
- **Simple** — minimal setup, works out of the box
- **Modular** — camera and display units can be upgraded independently
- **Open source** — hardware and software published openly

---

## 4. Hardware Architecture

### 4.1 Camera Unit (Headrest Mounted)

| Component | Selection | Notes |
|-----------|-----------|-------|
| Compute | Raspberry Pi Zero 2W | Low power, WiFi built in, ~$15 |
| Camera | Pi Camera Module 3 Wide | 120° FOV, good low light |
| Pan/Tilt | Two micro servo motors | Controlled via Pi GPIO |
| Battery | LiPo 3.7V ~2000mAh | Estimated 4-6 hours runtime |
| Enclosure | Custom 3D printed | Designed in Fusion 360 |
| Mount | Headrest post clamp | Tool-free attachment/removal |

**Camera unit responsibilities:**
- Capture and stream video over WiFi (MJPEG or WebRTC)
- Accept pan/tilt control commands from display unit
- Serve a lightweight web interface as fallback
- Auto-start on power-up
- Broadcast as WiFi hotspot OR connect to existing network

### 4.2 Display Unit (User Mounted)

| Component | Selection | Notes |
|-----------|-----------|-------|
| Compute | ESP32-S3 | WiFi, enough CPU for video decode |
| Display | 5" color LCD touchscreen | ~480x320 or better |
| Battery | LiPo 3.7V ~3000mAh | Estimated 6-8 hours runtime |
| Enclosure | Custom 3D printed | Designed in Fusion 360 |
| Mount | RAM mount compatible | Universal mounting options |

**Display unit responsibilities:**
- Connect to camera unit WiFi
- Receive and display video stream
- Send pan/tilt control commands via touchscreen swipe/tap
- Show battery status for both units
- Auto-connect on power-up

### 4.3 Browser-Based Access (Any Device)

The camera unit serves a responsive web interface directly from the Pi Zero 2W.
**No app installation required.** Any device with a browser works:

- Smartphone (iOS or Android)
- Tablet
- Laptop
- Any other WiFi-capable device with a browser

Simply connect the device to the camera unit's WiFi network and open a browser.
The interface provides:

- Full MJPEG video stream
- Touch/click-to-pan controls (tap where you want the camera to look)
- Swipe gestures for smooth pan/tilt
- Works on any screen size — fully responsive design
- No app store, no installation, no compatibility issues

This makes the system maximally accessible — users can choose the dedicated
ESP32-S3 display unit for a self-contained experience, or use any phone or
tablet they already own.

### 4.4 Communication

- **Protocol:** WiFi (2.4GHz)
- **Mode:** Camera unit acts as WiFi access point, display unit connects to it
- **Video:** MJPEG stream (simple, low latency, ESP32-S3 compatible)
- **Control:** UDP commands for pan/tilt (low latency)
- **No pairing required** — fixed SSID/password, just power on both units

---

## 5. Software Architecture

### 5.1 Camera Unit Software (Raspberry Pi Zero 2W)

- **OS:** Raspberry Pi OS Lite (minimal, fast boot)
- **Language:** Python (consistent with Hybrid RobotiX standards)
- **Video:** `picamera2` library → MJPEG stream server
- **Pan/Tilt:** `gpiozero` or `RPi.GPIO` servo control
- **Control server:** UDP listener for pan/tilt commands from display unit
- **Web interface:** Lightweight HTTP server serving responsive browser UI
  (MJPEG stream + touch pan/tilt controls — works on any phone/tablet)
- **Auto-start:** systemd service
- **WiFi AP:** hostapd + dnsmasq

### 5.2 Display Unit Software (ESP32-S3)

- **Framework:** Arduino or ESP-IDF
- **Video:** MJPEG decoder → display framebuffer
- **UI:** Touch input → pan/tilt UDP commands
- **WiFi:** Station mode, auto-connect to camera unit AP

---

## 6. Physical Design

### 6.1 Camera Unit Enclosure

- Weatherproof (splash resistant minimum)
- Clean headrest post clamp — no tools required to install/remove
- Camera lens protected when not in use (flip cover)
- LED indicator for power/streaming status
- USB-C charging port accessible without removal
- Pan range: ±90° horizontal
- Tilt range: -30° to +45° vertical

### 6.2 Display Unit Enclosure

- RAM mount ball adapter (industry standard, compatible with most mounts)
- Portrait and landscape orientation supported
- USB-C charging port
- Power button with LED indicator
- Rubberized grip surface

---

## 7. Target Market

- Power wheelchair users
- Manual wheelchair users with limited head/neck mobility
- Scooter users
- Anyone with limited rearward visibility due to disability

**Distribution channel:** Direct via The Accessibility Files / Hybrid RobotiX  
**Potential partners:** Disability organizations, DME suppliers, VA/rehab centers

---

## 8. Target Price Point

| Component | Estimated Cost |
|-----------|---------------|
| Pi Zero 2W + camera | ~$30 |
| Servos + hardware | ~$10 |
| LiPo battery + charging | ~$15 |
| ESP32-S3 + display | ~$25 |
| LiPo battery + charging | ~$12 |
| 3D printed enclosures | ~$10 |
| Miscellaneous | ~$8 |
| **Total BOM** | **~$110** |

**Target retail price:** $199–$249  
**Margin:** Sufficient to sustain The Accessibility Files mission

---

## 9. Development Phases

### Phase 1 — Proof of Concept
- [ ] Pi Zero 2W streaming MJPEG to browser
- [ ] Pan/tilt working via web interface
- [ ] ESP32-S3 displaying MJPEG stream
- [ ] Basic UDP pan/tilt control from ESP32-S3

### Phase 2 — Prototype
- [ ] Enclosure v1 designed in Fusion 360
- [ ] 3D printed on Bambu H2S
- [ ] Headrest mount designed and printed
- [ ] Battery management integrated
- [ ] Auto-start and auto-connect working

### Phase 3 — Field Test
- [ ] Mounted on My Chairiet for real-world testing
- [ ] Battery life validated
- [ ] Video latency measured and optimized
- [ ] Mount design refined from real use

### Phase 4 — Production Design
- [ ] Enclosure v2 — production quality
- [ ] PCB design for clean power management
- [ ] Assembly documentation
- [ ] User manual

### Phase 5 — Launch
- [ ] The Accessibility Files feature
- [ ] Hybrid RobotiX product page
- [ ] Open source release

---

## 10. Future Enhancements

- Object detection / proximity warning (BrainChip Akida or Hailo)
- License plate recognition
- Night vision (IR illumination)
- Wide-angle fisheye option
- Integration with My Chairiet HUD
- Multi-camera support (side cameras)
- Recording capability

---

*Document is a living design artifact. Architecture evolves as development progresses.*  
*— Dale — Hybrid RobotiX / The Accessibility Files*  
*"I. WILL. NEVER. GIVE. UP. OR. SURRENDER."*

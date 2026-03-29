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

## 2. Designer's Perspective

This product is designed by a power wheelchair user who rides mass transit daily.
Every design decision comes from real lived experience — not assumptions, not
focus groups, not guesswork.

The designer knows firsthand:
- How mirrors obstruct doorways and bus ramps
- How mirrors catch on transit vehicle doors and fixtures
- How critical rearward awareness is when backing onto a bus lift
- How useless fixed mirrors are for dynamic environments like crowded platforms
- What it feels like to navigate a subway platform without knowing what is behind you

This is what makes The Accessibility Files credible — *I investigate the
inaccessible* because I live the inaccessible every single day.

---

## 3. Problem Statement

Power wheelchair users have severely limited rearward visibility. Turning to
look behind is difficult or impossible for many users. This creates real safety
hazards in:

- Reversing in tight spaces
- Navigating crowded environments
- Detecting approaching people or vehicles from behind
- Parking and positioning
- **Boarding and exiting mass transit vehicles** — bus lifts, subway platforms,
  light rail gaps, paratransit vehicles

### Why mirrors fail

Mirrors are the current standard solution — and they are inadequate:

- Must be physically moved out of the way for doorways and bus ramps
- Protrude from the chair and **catch on transit vehicle doors and fixtures**
- Fixed angle — cannot pan to look where you need
- Useless in low light
- Obstructed by passengers in crowded environments
- Create additional width that complicates navigation in tight spaces

**This system has zero impact on boarding and exiting mass transit vehicles.**
When not in use, the camera unit sits flush against the headrest. No protrusion,
no obstruction, nothing to catch on doors or ramps.

---

## 4. Design Philosophy

- **Wireless** — no cables between camera and display units
- **Battery operated** — both units independent, no wiring into the wheelchair
- **Affordable** — target price accessible to disabled users on fixed incomes
- **Simple** — minimal setup, works out of the box
- **Modular** — camera and display units can be upgraded independently
- **Open source** — hardware and software published openly

---

## 5. Hardware Architecture

### 5.1 Camera Unit (Headrest Mounted)

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

### 5.2 Display Unit (User Mounted)

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

### 5.3 Browser-Based Access (Any Device)

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

### 5.4 Communication

- **Protocol:** WiFi (2.4GHz)
- **Mode:** Camera unit acts as WiFi access point, display unit connects to it
- **Video:** MJPEG stream (simple, low latency, ESP32-S3 compatible)
- **Control:** UDP commands for pan/tilt (low latency)
- **No pairing required** — fixed SSID/password, just power on both units

---

## 6. Software Architecture

### 6.1 Camera Unit Software (Raspberry Pi Zero 2W)

- **OS:** Raspberry Pi OS Lite (minimal, fast boot)
- **Language:** Python (consistent with Hybrid RobotiX standards)
- **Video:** `picamera2` library → MJPEG stream
- **Pan/Tilt:** `gpiozero` servo control via GPIO
- **Web framework:** Flask — serves the browser interface and MJPEG stream
- **Control:** Flask routes handle pan/tilt commands from any browser
- **Auto-start:** systemd service
- **WiFi AP:** hostapd + dnsmasq
- **mDNS hostname:** `headcam.local` — no IP address needed

**Flask routes:**
```
GET  /              — Serve responsive HTML/JS web interface
GET  /stream        — MJPEG video stream endpoint
POST /pan_tilt      — Receive pan/tilt commands (JSON)
GET  /status        — Camera unit status (battery, uptime, etc.)
```

**Access from any device:**
```
http://headcam.local        — Connect phone/tablet/laptop to camera WiFi,
                              open any browser, navigate to this URL.
                              No app, no installation, no account required.
```

**Python dependencies:**
- `flask` — web framework
- `picamera2` — camera interface
- `gpiozero` — servo control
- All installed into a virtualenv on the Pi Zero 2W

### 6.2 Display Unit Software (ESP32-S3)

- **Framework:** Arduino or ESP-IDF
- **Video:** MJPEG decoder → display framebuffer
- **UI:** Touch input → pan/tilt UDP commands
- **WiFi:** Station mode, auto-connect to camera unit AP

---

## 7. Physical Design

### 7.0 Thermal Management

The Pi Zero 2W runs warm under sustained camera streaming. Thermal management
is a first-class design concern, not an afterthought.

**Hardware measures:**
- Small adhesive heatsink on the SoC (~$2, included in BOM)
- Enclosure design must include ventilation slots
- Heatsink must have clearance inside the enclosure

**Software monitoring:**
- CPU temperature logged continuously via `/sys/class/thermal/thermal_zone0/temp`
- Temperature published to Flask `/status` endpoint
- Warning threshold: 70°C
- Throttle threshold: 80°C (Pi Zero 2W will self-throttle at this point)
- If temperature exceeds 75°C, stream resolution automatically reduced
- Temperature displayed in the browser interface

**Operating environment:**
- Outdoor use in direct sunlight is a concern — enclosure color matters
  (light colors reflect heat, dark colors absorb it)
- Default enclosure color: light grey or white
- User advised to avoid prolonged direct sunlight exposure

### 7.1 Mounting System

The camera unit mounts directly to the existing headrest support rods —
the same rods the headrest itself is mounted on. This is a universal solution
that works on virtually any power wheelchair without modification.

**Design principles:**
- No drilling, no permanent modifications to the wheelchair
- Tool-free installation and removal
- Adjustable height along the rod
- Adjustable rotation/angle around the rod
- Clamp spans both headrest rods for stability
- Designed in Fusion 360, printed on Bambu H2S

**Clamp design:**
- Split clamp with captive bolt — one-hand tightening
- Rod diameter range: accommodates common headrest rod diameters
  (typically 10mm–16mm — exact range TBD from field measurements on My Chairiet)
- Rubber liner inside clamp to protect rod finish and prevent slipping
- Camera unit docks into clamp via quick-release mechanism
- Camera unit can be removed without removing clamp from rods

**Advantages over mirror-based solutions:**
- No protruding hardware to catch on doorways or bus ramps
- Does not interfere with getting on/off mass transit vehicles
- Does not obstruct when not in use
- Works in any lighting condition
- Pan/tilt gives full situational awareness, not a fixed angle

### 7.2 Camera Unit Enclosure

- Weatherproof (splash resistant minimum)
- Camera lens protected when not in use (flip cover or retractable shroud)
- LED indicator for power/streaming status
- USB-C charging port accessible without removing unit from mount
- Light grey or white color to minimize solar heat absorption
- Pan range: ±90° horizontal
- Tilt range: -30° to +45° vertical

### 7.3 Display Unit Enclosure

- RAM mount ball adapter (industry standard, compatible with most mounts)
- Portrait and landscape orientation supported
- USB-C charging port
- Power button with LED indicator
- Rubberized grip surface

---

## 8. Target Market

- Power wheelchair users
- Manual wheelchair users with limited head/neck mobility
- Scooter users
- Anyone with limited rearward visibility due to disability

**Distribution channel:** Direct via The Accessibility Files / Hybrid RobotiX  
**Potential partners:** Disability organizations, DME suppliers, VA/rehab centers

---

## 9. Target Price Point

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

## 10. Development Phases

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

## 11. Future Enhancements

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

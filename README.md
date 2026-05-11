# MMS – Monitoring System for Rover

MMS is a desktop monitoring application developed for the MAVEN-01 rover platform. The system is built with Python and Qt to provide real-time telemetry monitoring, sensor visualization, and camera streaming through a clean and responsive graphical interface.

The application communicates with onboard sensors and embedded devices using the MQTT protocol over WiFi, allowing operators to monitor rover status remotely during testing and field operations.

---

# Features

- Real-time monitoring dashboard for MAVEN-01
- Live camera streaming from ESP32 camera module
- MQTT-based telemetry communication
- Sensor data visualization
- Rover health monitoring
- Battery and connectivity status tracking
- Gyroscope and orientation display
- Environmental monitoring
- Lightweight and responsive Qt interface

---

# System Architecture

The MMS application receives telemetry and sensor data from the rover through MQTT topics over a wireless network.

Data sources include:

- ESP32 camera module
- Environmental sensors
- Battery management system
- Gyroscope and orientation sensors
- UDP communication status
- Direction and indicator systems


---

Environmental sensor information:

- Pressure
- Temperature
- Humidity


---
## DEMO

<img width="1096" height="725" alt="Screenshot 2026-05-11 at 07 47 48" src="https://github.com/user-attachments/assets/a097e239-1dad-461d-90d5-bfe4d9cc9392" />





Rover system status and control indicators:

- Battery monitoring
- Gyroscope visualization
- UDP connection status
- Direction indicators
- System activity lights


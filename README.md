# Top_HAT_Dashboard
The CirkitScape Web App lets you monitor sensors, control GPIOs, and communicate over RS-485—all from your browser. With built-in ADC and MCP23017 support, it makes prototyping, testing, and automation on the Raspberry Pi fast, simple, and code-free ... ish

# CirkitScape Web App

The **CirkitScape Web App** is a lightweight, browser-based interface for the **Top HAT expansion board for Raspberry Pi**. It enables rapid prototyping, sensor monitoring, and automation, without needing to write code.

---

## Features
- **ADC Monitoring** – View real-time sensor values using the onboard ADS1015.  
- **GPIO Control** – Configure and toggleGPIO pins via the MCP23017 expander and the RPi.  
- **RS-485 Communication** – Send and receive messages directly from the browser.  
- **Web Dashboard** – Accessible from any device on the same network.  
- **REST API** – Programmatic access to all functions for automation and integration.  

---

## Getting Started

### Prerequisites
- Raspberry Pi (3B/4/5 or Pi Zero 2 W recommended)  
- Top HAT expansion board installed  
- Python 3.9+  
- Required libraries:
  - Flask
  - smbus2
  - RPi.GPIO
  - pyserial  

**Running the App**
TopHatDashboard.py
Access the dashboard in your browser at:
👉 http://raspberrypi-ip:5000

 - TopHatDashboard.py  # Flask web app
 - adc_reader.py       # ADS1015 ADC functions
 - mcp_gpio.py         # MCP23017 GPIO expander functions
 - rpi_gpio.py         # MCP23017 GPIO expander functions
 - rs485_handler.py    # RS-485 communication functions
 - static/             # CSS/JS
 - templates/          # HTML templates

Example Use Cases

Test and validate industrial sensors quickly

Build custom automation dashboards

Prototype IoT projects before scaling to production

Classroom or lab teaching tool for Raspberry Pi

License

This project is licensed under the MIT License.

Contact

For support, feedback, or partnerships:
CirkitScape – https://www.cirkitscape.tech

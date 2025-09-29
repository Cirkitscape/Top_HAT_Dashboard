#!/usr/bin/env python3
"""
Flask web app for Top HAT
- Shows ADC readings
- Shows & controls MCP23017 GPIOs (A0–A7, B0–B7)
- Handles RS-485 send/receive
- USB device monitoring
- Raspberry Pi GPIO control
"""
import atexit
import logging
from flask import Flask, jsonify, render_template, request, abort
from adc_reader import read_all_channels
from mcp_gpio import setup_gpio, read_all, write_outputs, cleanup as mcp_cleanup
import rs485_handler
import usb_status
import rpi_gpio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Global state ---
current_outputs = {"A": 0x00, "B": 0x00}
hardware_status = {"mcp23017": False, "rs485": False, "rpi_gpio": False}

def init_hardware():
    """Initialize all hardware components with graceful error handling."""
    hardware_status = {
        "mcp23017": False,
        "rs485": False,
        "rpi_gpio": False
    }
    
    # Init MCP23017 (non-critical - continue if it fails)
    try:
        setup_gpio(dir_a=0x00, dir_b=0x00)
        hardware_status["mcp23017"] = True
        logger.info("MCP23017 GPIO initialized")
    except Exception as e:
        logger.warning(f"MCP23017 initialization failed: {e}")
        logger.info("Continuing without MCP23017 support")
    
    # Init RS-485 (non-critical - continue if it fails)
    try:
        rs485_handler.init_gpio()
        rs485_handler.start_listener()
        hardware_status["rs485"] = True
        logger.info("RS-485 handler initialized")
    except Exception as e:
        logger.warning(f"RS-485 initialization failed: {e}")
        logger.info("Continuing without RS-485 support")
    
    # Init Raspberry Pi GPIO (most likely to succeed)
    try:
        if rpi_gpio.init_rpi_gpio():
            rpi_gpio.init_default_pins()
            hardware_status["rpi_gpio"] = True
            logger.info("Raspberry Pi GPIO initialized")
        else:
            logger.warning("Failed to initialize Raspberry Pi GPIO")
    except Exception as e:
        logger.warning(f"Raspberry Pi GPIO initialization failed: {e}")
    
    # Log overall status
    working_components = sum(hardware_status.values())
    logger.info(f"Hardware initialization complete: {working_components}/3 components working")
    
    if working_components == 0:
        logger.error("No hardware components initialized successfully!")
        raise Exception("Critical hardware initialization failure")
    
    return hardware_status

def cleanup_hardware():
    """Clean up all hardware resources."""
    try:
        mcp_cleanup()
        rs485_handler.cleanup()
        rpi_gpio.cleanup_rpi_gpio()
        logger.info("Hardware cleanup completed")
    except Exception as e:
        logger.error(f"Hardware cleanup failed: {e}")

# Register cleanup function to run on exit
atexit.register(cleanup_hardware)

@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")

@app.route("/json")
def json_data():
    """Return ADC + GPIO + RS-485 + USB + RPi GPIO data in JSON format."""
    try:
        response_data = {
            "hardware_status": hardware_status
        }
        
        # Only try to read ADC if available
        try:
            adc_data = read_all_channels()
            response_data["adc"] = adc_data
        except Exception as e:
            logger.debug(f"ADC read failed: {e}")
            response_data["adc"] = {}
        
        # Only try to read MCP23017 GPIO if initialized
        if hardware_status["mcp23017"]:
            try:
                a_val, b_val = read_all()
                response_data["gpio"] = {
                    "A": format(a_val, "08b"),
                    "B": format(b_val, "08b")
                }
                response_data["outputs"] = current_outputs
            except Exception as e:
                logger.debug(f"MCP23017 read failed: {e}")
                response_data["gpio"] = {"A": "00000000", "B": "00000000"}
                response_data["outputs"] = current_outputs
        else:
            response_data["gpio"] = {"A": "00000000", "B": "00000000"}
            response_data["outputs"] = current_outputs
        
        # Only try to read RS-485 if initialized
        if hardware_status["rs485"]:
            try:
                last_msg = rs485_handler.get_last_message()
                response_data["rs485_last"] = last_msg
            except Exception as e:
                logger.debug(f"RS-485 read failed: {e}")
                response_data["rs485_last"] = None
        else:
            response_data["rs485_last"] = None
        
        # USB status (usually works)
        try:
            response_data["usb_connected"] = usb_status.usb_connected()
            response_data["usb_devices"] = usb_status.list_usb_devices()
        except Exception as e:
            logger.debug(f"USB read failed: {e}")
            response_data["usb_connected"] = False
            response_data["usb_devices"] = []
        
        # RPi GPIO (should usually work)
        if hardware_status["rpi_gpio"]:
            try:
                response_data["rpi_gpio"] = {
                    "configs": rpi_gpio.get_all_configs(),
                    "states": rpi_gpio.get_all_pin_states(),
                    "safe_pins": rpi_gpio.get_safe_pins()
                }
            except Exception as e:
                logger.debug(f"RPi GPIO read failed: {e}")
                response_data["rpi_gpio"] = {
                    "configs": {},
                    "states": {},
                    "safe_pins": []
                }
        else:
            response_data["rpi_gpio"] = {
                "configs": {},
                "states": {},
                "safe_pins": []
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error reading sensor data: {e}")
        return jsonify({"error": "Failed to read sensor data"}), 500

@app.route("/gpio/write/<port>/<int:pin>/<int:state>", methods=["POST"])
def gpio_write(port, pin, state):
    """Toggle a single MCP23017 output pin."""
    current_outputs
    
    # Check if MCP23017 is available
    if not hardware_status["mcp23017"]:
        return jsonify({"error": "MCP23017 not available"}), 503
    
    # Validate inputs
    port = port.upper()
    if port not in ["A", "B"]:
        abort(400, "Port must be 'A' or 'B'")
    
    if not (0 <= pin <= 7):
        abort(400, "Pin must be between 0 and 7")
    
    if state not in [0, 1]:
        abort(400, "State must be 0 or 1")
    
    try:
        mask = 1 << pin
        if state == 1:
            current_outputs[port] |= mask
        else:
            current_outputs[port] &= ~mask
        
        write_outputs(current_outputs["A"], current_outputs["B"])
        logger.info(f"GPIO {port}{pin} set to {state}")
        
        return jsonify({
            "success": True,
            "port": port,
            "pin": pin,
            "state": state,
            "outputs": current_outputs
        })
        
    except Exception as e:
        logger.error(f"GPIO write error: {e}")
        return jsonify({"error": "Failed to write GPIO"}), 500

@app.route("/rpi_gpio/setup/<int:pin>/<mode>", methods=["POST"])
def rpi_gpio_setup(pin, mode):
    """Setup a Raspberry Pi GPIO pin as input or output."""
    # Check if RPi GPIO is available
    if not hardware_status["rpi_gpio"]:
        return jsonify({"error": "Raspberry Pi GPIO not available"}), 503
        
    try:
        if pin not in rpi_gpio.get_safe_pins():
            return jsonify({"error": f"Pin {pin} is not safe to use"}), 400
        
        if mode.upper() not in ["IN", "OUT"]:
            return jsonify({"error": "Mode must be 'IN' or 'OUT'"}), 400
        
        import RPi.GPIO as GPIO
        gpio_mode = GPIO.OUT if mode.upper() == "OUT" else GPIO.IN
        
        success = rpi_gpio.setup_pin(pin, gpio_mode)
        
        if success:
            return jsonify({
                "success": True,
                "pin": pin,
                "mode": mode.upper(),
                "configs": rpi_gpio.get_all_configs(),
                "states": rpi_gpio.get_all_pin_states()
            })
        else:
            return jsonify({"error": f"Failed to setup pin {pin}"}), 500
            
    except Exception as e:
        logger.error(f"RPi GPIO setup error: {e}")
        return jsonify({"error": "Failed to setup GPIO pin"}), 500

@app.route("/rpi_gpio/write/<int:pin>/<int:state>", methods=["POST"])
def rpi_gpio_write(pin, state):
    """Set a Raspberry Pi GPIO output pin high or low."""
    # Check if RPi GPIO is available
    if not hardware_status["rpi_gpio"]:
        return jsonify({"error": "Raspberry Pi GPIO not available"}), 503
        
    try:
        if state not in [0, 1]:
            return jsonify({"error": "State must be 0 or 1"}), 400
        
        success = rpi_gpio.set_pin_output(pin, state)
        
        if success:
            return jsonify({
                "success": True,
                "pin": pin,
                "state": state,
                "states": rpi_gpio.get_all_pin_states()
            })
        else:
            return jsonify({"error": f"Failed to set pin {pin}"}), 500
            
    except Exception as e:
        logger.error(f"RPi GPIO write error: {e}")
        return jsonify({"error": "Failed to write GPIO pin"}), 500

@app.route("/rpi_gpio/reset/<int:pin>", methods=["POST"])
def rpi_gpio_reset(pin):
    """Reset a Raspberry Pi GPIO pin to input mode."""
    # Check if RPi GPIO is available
    if not hardware_status["rpi_gpio"]:
        return jsonify({"error": "Raspberry Pi GPIO not available"}), 503
        
    try:
        success = rpi_gpio.reset_pin(pin)
        
        if success:
            return jsonify({
                "success": True,
                "pin": pin,
                "configs": rpi_gpio.get_all_configs(),
                "states": rpi_gpio.get_all_pin_states()
            })
        else:
            return jsonify({"error": f"Failed to reset pin {pin}"}), 500
            
    except Exception as e:
        logger.error(f"RPi GPIO reset error: {e}")
        return jsonify({"error": "Failed to reset GPIO pin"}), 500

@app.route("/rs485/send", methods=["POST"])
def rs485_send():
    """Send a message over RS-485."""
    # Check if RS-485 is available
    if not hardware_status["rs485"]:
        return jsonify({"error": "RS-485 not available"}), 503
        
    try:
        # Handle both JSON and form data
        if request.is_json:
            msg = request.json.get("msg")
        else:
            msg = request.form.get("msg")
        
        if not msg or not msg.strip():
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Limit message length for safety
        if len(msg) > 255:
            return jsonify({"error": "Message too long (max 255 chars)"}), 400
        
        success = rs485_handler.send_message(msg.strip())
        
        if success:
            logger.info(f"RS-485 message sent: {msg}")
            return jsonify({"success": True, "sent": msg})
        else:
            logger.error(f"Failed to send RS-485 message: {msg}")
            return jsonify({"error": "Failed to send message"}), 500
            
    except Exception as e:
        logger.error(f"RS-485 send error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/rs485/last")
def rs485_last():
    """Return most recent RS-485 message received."""
    try:
        last_msg = rs485_handler.get_last_message()
        return jsonify({"last": last_msg})
    except Exception as e:
        logger.error(f"RS-485 read error: {e}")
        return jsonify({"error": "Failed to read RS-485 data"}), 500

@app.route("/usb")
def usb_check():
    """Return current USB status + device list."""
    try:
        return jsonify({
            "usb_connected": usb_status.usb_connected(),
            "usb_devices": usb_status.list_usb_devices()
        })
    except Exception as e:
        logger.error(f"USB status error: {e}")
        return jsonify({"error": "Failed to read USB status"}), 500

@app.route("/health")
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        "status": "healthy",
        "services": ["adc", "gpio", "rs485", "usb", "rpi_gpio"]
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    try:
        # Initialize hardware before starting the server
        hardware_status = init_hardware()
        
        # Run the Flask application
        app.run(
            host="0.0.0.0", 
            port=5000, 
            debug=False,  # Set to False for production
            threaded=True  # Enable threading for better performance
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        logger.info("Starting with limited functionality...")
        # Try to run with whatever components are working
        hardware_status = {"mcp23017": False, "rs485": False, "rpi_gpio": False}
        app.run(
            host="0.0.0.0", 
            port=5000, 
            debug=False,
            threaded=True
        )
    finally:
        cleanup_hardware()

#!/usr/bin/env python3
"""
rpi_gpio.py
Raspberry Pi GPIO control module
- Controls individual GPIO pins
- Reads pin states
- Safe initialization and cleanup
"""
import RPi.GPIO as GPIO
import logging

logger = logging.getLogger(__name__)

# Common GPIO pins that are safe to use (avoiding I2C, SPI, UART pins and user-specified pins)
# Excluded physical pins: 3, 5, 8, 10, 12, 13, 29, 31, 32, 33
# Excluded BCM pins: 2, 3, 14, 19, 18, 27, 5, 6, 12, 13
SAFE_PINS = [4, 17, 22, 10, 9, 11, 26, 15, 23, 24, 25, 8, 7, 16, 20, 21]

# Current pin configurations
pin_configs = {}
pin_states = {}

def init_rpi_gpio():
    """Initialize Raspberry Pi GPIO system."""
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        logger.info("Raspberry Pi GPIO initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize RPi GPIO: {e}")
        return False

def setup_pin(pin, mode, initial_state=GPIO.LOW):
    """Setup a GPIO pin as input or output."""
    try:
        if pin not in SAFE_PINS:
            logger.warning(f"Pin {pin} is not in the safe pins list")
            return False
        
        if mode == GPIO.OUT:
            GPIO.setup(pin, GPIO.OUT, initial=initial_state)
            pin_states[pin] = initial_state
        else:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            pin_states[pin] = GPIO.input(pin)
        
        pin_configs[pin] = mode
        logger.info(f"Pin {pin} setup as {'OUTPUT' if mode == GPIO.OUT else 'INPUT'}")
        return True
    except Exception as e:
        logger.error(f"Failed to setup pin {pin}: {e}")
        return False

def set_pin_output(pin, state):
    """Set an output pin high or low."""
    try:
        if pin not in pin_configs:
            logger.error(f"Pin {pin} not configured")
            return False
        
        if pin_configs[pin] != GPIO.OUT:
            logger.error(f"Pin {pin} is not configured as output")
            return False
        
        GPIO.output(pin, state)
        pin_states[pin] = state  # ✅ Store last commanded state
        logger.info(f"Pin {pin} set to {'HIGH' if state else 'LOW'}")
        return True
    except Exception as e:
        logger.error(f"Failed to set pin {pin}: {e}")
        return False

def get_pin_state(pin):
    """Get the current state of a pin."""
    try:
        if pin not in pin_configs:
            return None

        # ✅ If OUTPUT, return last commanded state (don’t re-read hardware)
        if pin_configs[pin] == GPIO.OUT:
            return pin_states.get(pin, GPIO.LOW)

        # If INPUT, read actual hardware
        current_state = GPIO.input(pin)
        pin_states[pin] = current_state
        return current_state
    except Exception as e:
        logger.error(f"Failed to read pin {pin}: {e}")
        return None

def get_all_pin_states():
    """Get states of all configured pins."""
    states = {}
    for pin in pin_configs:
        states[pin] = get_pin_state(pin)
    return states

def get_pin_config(pin):
    """Get the configuration of a pin."""
    return pin_configs.get(pin)

def get_all_configs():
    """Get all pin configurations."""
    return pin_configs.copy()

def reset_pin(pin):
    """Reset a pin to unconfigured state (completely remove from GPIO)."""
    try:
        if pin in pin_configs:
            # Clean up the pin completely
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
            GPIO.cleanup(pin)  # This removes the pin from GPIO control
            del pin_configs[pin]
            if pin in pin_states:
                del pin_states[pin]
            logger.info(f"Pin {pin} reset to unconfigured state")
            return True
    except Exception as e:
        logger.error(f"Failed to reset pin {pin}: {e}")
    return False

def cleanup_rpi_gpio():
    """Clean up GPIO resources."""
    try:
        GPIO.cleanup()
        pin_configs.clear()
        pin_states.clear()
        logger.info("Raspberry Pi GPIO cleanup completed")
    except Exception as e:
        logger.error(f"GPIO cleanup error: {e}")

def get_safe_pins():
    """Return list of safe GPIO pins to use."""
    return SAFE_PINS.copy()

# Initialize some common pins as outputs for testing
def init_default_pins():
    """Initialize some default pins for the web interface."""
    default_output_pins = [23, 24, 25]  # Safe GPIO pins that won't interfere with I2C
    
    for pin in default_output_pins:
        setup_pin(pin, GPIO.OUT, GPIO.LOW)

if __name__ == "__main__":
    # Test the module
    if init_rpi_gpio():
        init_default_pins()
        print("Available pins:", get_safe_pins())
        print("Configured pins:", get_all_configs())
        print("Pin states:", get_all_pin_states())
        cleanup_rpi_gpio()

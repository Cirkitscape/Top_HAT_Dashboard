#!/usr/bin/env python3
"""
MCP23017 GPIO Library
- Provides setup, read, write, and cleanup helpers.
- Uses Raspberry Pi GPIO pin 18 as MCP reset (optional).
"""

import time
import RPi.GPIO as GPIO
import logging

logger = logging.getLogger(__name__)

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# ---- Raspberry Pi & I2C settings ----
I2C_BUS_NUM = 1
MCP23017_ADDR = 0x20      # Adjust if A2..A0 not tied to GND
MCP_RESET_BCM = 18        # Physical pin 12 (optional reset)

# ---- MCP23017 registers ----
IODIRA = 0x00
IODIRB = 0x01
GPIOA  = 0x12
GPIOB  = 0x13
OLATA  = 0x14
OLATB  = 0x15

# Track if we've initialized the reset pin
_reset_pin_initialized = False

def _init_reset_pin():
    """Initialize the MCP23017 reset pin if not already done."""
    global _reset_pin_initialized
    if not _reset_pin_initialized:
        try:
            # Only initialize if not already set by rpi_gpio module
            GPIO.setwarnings(False)
            if GPIO.getmode() is None:
                GPIO.setmode(GPIO.BCM)
            
            # Set reset pin high (inactive reset)
            GPIO.setup(MCP_RESET_BCM, GPIO.OUT, initial=GPIO.HIGH)
            _reset_pin_initialized = True
            logger.info(f"MCP23017 reset pin {MCP_RESET_BCM} initialized")
        except Exception as e:
            logger.warning(f"Could not initialize MCP23017 reset pin: {e}")

def reset_mcp23017():
    """Perform a hardware reset of the MCP23017."""
    try:
        _init_reset_pin()
        if _reset_pin_initialized:
            GPIO.output(MCP_RESET_BCM, GPIO.LOW)   # Assert reset
            time.sleep(0.001)  # Hold reset for 1ms
            GPIO.output(MCP_RESET_BCM, GPIO.HIGH)  # Release reset
            time.sleep(0.01)   # Wait for chip to come up
            logger.info("MCP23017 hardware reset performed")
    except Exception as e:
        logger.warning(f"MCP23017 reset failed: {e}")

def setup_gpio(dir_a=0x00, dir_b=0x00):
    """
    Initialize MCP23017 GPIO directions.
    dir_a: bit mask for GPIOA (0=output, 1=input)
    dir_b: bit mask for GPIOB (0=output, 1=input)
    """
    try:
        # Try hardware reset first
        reset_mcp23017()
        
        with SMBus(I2C_BUS_NUM) as bus:
            bus.write_byte_data(MCP23017_ADDR, IODIRA, dir_a)
            bus.write_byte_data(MCP23017_ADDR, IODIRB, dir_b)
            # Clear outputs at start
            bus.write_byte_data(MCP23017_ADDR, OLATA, 0x00)
            bus.write_byte_data(MCP23017_ADDR, OLATB, 0x00)
            logger.info("MCP23017 GPIO initialized successfully")
    except Exception as e:
        logger.error(f"MCP23017 setup failed: {e}")
        raise

def read_all():
    """Read GPIOA + GPIOB states from MCP23017. Returns (a, b)."""
    try:
        with SMBus(I2C_BUS_NUM) as bus:
            a = bus.read_byte_data(MCP23017_ADDR, GPIOA)
            b = bus.read_byte_data(MCP23017_ADDR, GPIOB)
        return a, b
    except Exception as e:
        logger.error(f"MCP23017 read failed: {e}")
        raise

def write_outputs(port_a_val=0x00, port_b_val=0x00):
    """Write values to MCP23017 outputs (A and B)."""
    try:
        with SMBus(I2C_BUS_NUM) as bus:
            bus.write_byte_data(MCP23017_ADDR, OLATA, port_a_val)
            bus.write_byte_data(MCP23017_ADDR, OLATB, port_b_val)
    except Exception as e:
        logger.error(f"MCP23017 write failed: {e}")
        raise

def cleanup():
    """Release MCP23017 related GPIO resources."""
    global _reset_pin_initialized
    try:
        if _reset_pin_initialized:
            # Only cleanup our reset pin, don't call GPIO.cleanup() 
            # as it would interfere with rpi_gpio module
            GPIO.setup(MCP_RESET_BCM, GPIO.IN)
            _reset_pin_initialized = False
            logger.info("MCP23017 reset pin cleaned up")
    except Exception as e:
        logger.warning(f"MCP23017 cleanup warning: {e}")

if __name__ == "__main__":
    # Test the module
    try:
        setup_gpio(dir_a=0x00, dir_b=0x00)  # All outputs
        write_outputs(0xFF, 0xFF)  # All high
        time.sleep(1)
        a, b = read_all()
        print(f"Port A: 0x{a:02x}, Port B: 0x{b:02x}")
        write_outputs(0x00, 0x00)  # All low
        cleanup()
    except Exception as e:
        print(f"Test failed: {e}")
        cleanup()

"""
usb_status.py
Enhanced USB device monitoring with device listing and caching
"""

import subprocess
import logging
import re
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Cache results for 5 seconds to avoid excessive system calls
CACHE_TIMEOUT = 5
_last_cache_time = 0
_cached_devices = []

def usb_connected():
    """Return True if any USB devices are connected, False otherwise."""
    try:
        result = subprocess.run(
            ["lsusb"], 
            capture_output=True, 
            text=True, 
            timeout=5  # Prevent hanging
        )
        
        if result.returncode != 0:
            logger.warning(f"lsusb returned error code {result.returncode}")
            return False
            
        # Filter out the root hub entries (they're always present)
        lines = result.stdout.strip().split('\n')
        device_lines = [line for line in lines if line and 'root hub' not in line.lower()]
        
        return len(device_lines) > 0
        
    except subprocess.TimeoutExpired:
        logger.error("lsusb command timed out")
        return False
    except Exception as e:
        logger.error(f"USB check failed: {e}")
        return False

def list_usb_devices():
    """Return a list of connected USB devices with details."""
    global _last_cache_time, _cached_devices
    
    # Return cached results if still valid
    current_time = time.time()
    if current_time - _last_cache_time < CACHE_TIMEOUT:
        return _cached_devices
    
    try:
        result = subprocess.run(
            ["lsusb"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode != 0:
            logger.warning(f"lsusb returned error code {result.returncode}")
            return []
        
        devices = []
        for line in result.stdout.strip().split('\n'):
            if line and 'root hub' not in line.lower():
                device_info = parse_usb_line(line)
                if device_info:
                    devices.append(device_info)
        
        # Update cache
        _cached_devices = devices
        _last_cache_time = current_time
        
        return devices
        
    except subprocess.TimeoutExpired:
        logger.error("lsusb command timed out")
        return []
    except Exception as e:
        logger.error(f"Failed to list USB devices: {e}")
        return []

def parse_usb_line(line):
    """Parse a single line from lsusb output."""
    try:
        # Example: "Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub"
        # Pattern: Bus XXX Device YYY: ID XXXX:YYYY Description
        pattern = r'Bus (\d+) Device (\d+): ID ([0-9a-f]{4}):([0-9a-f]{4})\s*(.*)'
        match = re.match(pattern, line, re.IGNORECASE)
        
        if match:
            bus, device, vendor_id, product_id, description = match.groups()
            return {
                "bus": int(bus),
                "device": int(device),
                "vendor_id": vendor_id,
                "product_id": product_id,
                "description": description.strip() or "Unknown Device",
                "id": f"{vendor_id}:{product_id}"
            }
    except Exception as e:
        logger.debug(f"Failed to parse USB line '{line}': {e}")
    
    return None

def get_device_count():
    """Return the number of connected USB devices (excluding root hubs)."""
    devices = list_usb_devices()
    return len(devices)

def find_device_by_id(vendor_id, product_id):
    """Find a specific USB device by vendor and product ID."""
    devices = list_usb_devices()
    target_id = f"{vendor_id:04x}:{product_id:04x}".lower()
    
    for device in devices:
        if device["id"].lower() == target_id:
            return device
    return None

def clear_cache():
    """Clear the device cache to force a refresh."""
    global _last_cache_time, _cached_devices
    _last_cache_time = 0
    _cached_devices = []

# For backward compatibility and testing
if __name__ == "__main__":
    print("USB Connected:", usb_connected())
    print("USB Devices:")
    for device in list_usb_devices():
        print(f"  {device['description']} (ID: {device['id']})")
    print(f"Total devices: {get_device_count()}")

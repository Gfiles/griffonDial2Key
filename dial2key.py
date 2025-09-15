# .\.venv\Scripts\pyinstaller --clean --onefile --add-data "libusb-1.0.dll;." dial2key.py

import json
import time
from pynput.keyboard import Key, Controller
import usb.core
import usb.util
import os

keyboard = Controller()

def read_config(settings_file):
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            return json.load(f)
    else:
        data = {
            "down" : "d",
            "up" : "a",
            "left" : "s",
            "right" : "a",
            "delay" : 0.2
        }
        json_data = json.dumps(data, indent=4)
        with open(settings_file, 'w') as f:
            f.write(json_data)

    return data

def list_usb_devices():
    """
    Finds and lists all connected USB devices with their details.
    """
    # Find all connected USB devices
    devices = usb.core.find(find_all=True)

    # If no devices are found, exit
    if not devices:
        print("No USB devices found.")
        return

    print("--- Connected USB Devices ---")
    # Iterate over all found devices
    for dev in devices:
        print_device_info(dev)

def find_and_read_specific_device(vendor_id, product_id):
    """
    Finds a specific USB device by its Vendor and Product ID and prints its details.
    """
    print(f"--- Searching for device with Vendor ID: {hex(vendor_id)} and Product ID: {hex(product_id)} ---")
    dev = usb.core.find(idVendor=vendor_id, idProduct=product_id)

    if dev is None:
        print("Device not found.")
        return

    print("Device found!")
    print_device_info(dev)

    # Now, let's try to read data from it in a loop
    read_from_device_loop(dev)

def print_device_info(dev):
    """
    Prints detailed information for a given usb.core.Device object.
    """
    try:
        # The following fields are directly available from the device descriptor
        print(f"Vendor ID: {hex(dev.idVendor)}")
        print(f"Product ID: {hex(dev.idProduct)}")

        # Manufacturer and Product strings are read from the device
        # and can raise an error if not available or if permissions are insufficient.
        manufacturer = usb.util.get_string(dev, dev.iManufacturer)
        product = usb.util.get_string(dev, dev.iProduct)
        serial = usb.util.get_string(dev, dev.iSerialNumber)

        if manufacturer:
            print(f"Manufacturer: {manufacturer}")
        if product:
            print(f"Product: {product}")
        if serial:
            print(f"Serial Number: {serial}")

    except usb.core.USBError as e:
        print(f"Could not read string descriptors for device {hex(dev.idVendor)}:{hex(dev.idProduct)}. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("-" * 30)

def read_from_device_loop(dev):
    """
    Claims the device and reads data from its IN endpoint in a continuous loop.
    """
    ep_in = None
    interface_number = -1

    try:
        # Set the active configuration. With no arguments, the first configuration is chosen.
        dev.set_configuration()
        print("Device configuration set.")

        # Get an interface descriptor
        cfg = dev.get_active_configuration()
        
        # Find the first available interface
        interface_number = cfg[(0,0)].bInterfaceNumber

        # Find the IN endpoint
        for ep in cfg[(0,0)]:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                ep_in = ep
                print(f"Found IN endpoint: {hex(ep.bEndpointAddress)}")
                break
        
        if ep_in is None:
            print("Error: Could not find an IN endpoint on the first interface.")
            return

        # Claim the interface. This is mandatory!
        usb.util.claim_interface(dev, interface_number)
        print(f"Claimed interface {interface_number}.")
        print("\n--- Starting to read data (press Ctrl+C to stop) ---")
        last_press_state = 0
        timer = 0
        key_down = config["down"]
        key_up = config["up"]
        key_left = config["left"]
        key_right = config["right"]
        delay = float(config["delay"])
        while True:
            try:
                # Read data from the endpoint.
                # The second argument is the timeout in milliseconds.
                data = ep_in.read(ep_in.wMaxPacketSize, 1000)
                #print(f"Received: {data}")
                # You can process the 'data' (which is a byte array) here.
                # For example: print(data.tobytes().decode('utf-8', errors='ignore'))
                #print(f"{data[0]} - {data[1]}")
                #non blovking timer
                if last_press_state != data[0]:
                    last_press_state = data[0]
                    if data[0] == 1:
                        print("Down")
                        keyboard.press(key_down)
                        keyboard.release(key_down)
                    elif data[0] == 0:
                        print("Up")
                        keyboard.press(key_up)
                        keyboard.release(key_up)

                if time.time() - timer > delay:
                    if data[1] == 1:
                        print("Right")
                        keyboard.press(key_right)
                        keyboard.release(key_right)
                    elif data[1] == 255:
                        print("Left")
                        keyboard.press(key_left)
                        keyboard.release(key_left)
                    timer = time.time()

            except usb.core.USBError as e:
                if e.args == ('Operation timed out',):
                    continue # Timeout is expected if the device sends data intermittently.
                #print(f"Data read error: {e}")
                #break # Exit loop on other errors

    except KeyboardInterrupt:
        print("\nStopping read loop.")
    finally:
        # This is crucial to release the interface for other programs.
        if interface_number != -1:
            usb.util.release_interface(dev, interface_number)
            print(f"Released interface {interface_number}.")
        # This frees the configuration.
        usb.util.dispose_resources(dev)
        print("Device resources disposed.")

if __name__ == "__main__":
    # Get current working directory
    current_dir = os.getcwd()
    settings_file = os.path.join(current_dir, "settings.json")
    config = read_config(settings_file)
    
    # Define the Vendor and Product IDs for the device you want to find
    TARGET_VENDOR_ID = 0x077d
    TARGET_PRODUCT_ID = 0x0410

    find_and_read_specific_device(TARGET_VENDOR_ID, TARGET_PRODUCT_ID)

    # To list all devices again, you can uncomment the line below
    list_usb_devices()
#!python3
import sys
import os
from time import sleep
import math
import subprocess
import re

# Create an image of a USB stick.
# USE MY SHITTY CODE AT YOUR OWN RISK.
# TODO implement compression: https://docs.python.org/3/library/lzma.html

class PhysicalDevice(object):
    """Container to store the output of
    `wmic diskdrive get DeviceId,TotalSectors,BytesPerSector,Model,InterfaceType`"""
    def __init__(self, bytes_per_sector, 
                       device_id, 
                       interface_type, 
                       model, 
                       total_sectors):
        self.bytes_per_sector = bytes_per_sector
        self.device_id = device_id
        self.interface_type = interface_type
        self.model = model
        self.total_sectors = total_sectors

def convert_size(size_bytes):
    """From James Sapam on Stack overflow: 
    https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python/14822210#14822210"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])

def dd(physical_device, destination, sector_read_amount=128000):
    sector_len = physical_device.bytes_per_sector
    sector_total = physical_device.total_sectors

    try:
        # Windows os.open flags docs:
        # https://msdn.microsoft.com/en-us/library/z0kc8e3z.aspx
        disk_fh = os.open(physical_device.device_id, 
                          os.O_BINARY | os.O_RDONLY | os.O_SEQUENTIAL)
    except PermissionError:
        print("You do not have enough permissions.")
        sys.exit(1)
    
    with open(destination, 'wb') as dest_fh:
        i = 0
        while i < sector_total:
            if i + sector_read_amount < sector_total:
                buffer = os.read(disk_fh, sector_len * sector_read_amount)
                i += sector_read_amount
            else:
                rest_sectors = sector_total - i
                buffer = os.read(disk_fh, sector_len * rest_sectors)
                i += rest_sectors

            dest_fh.write(buffer)
            sys.stdout.write((' ' * 80) + '\r')
            sys.stdout.write("%d sectors written (%s)" % 
                                             (i, convert_size(i * sector_len)))
       
        # I know this is ridiculous but sometimes WMI doesn't report the 
        # amount of sectors accurately. The only option here is now to 
        # attempt to read past the amount of reported sectors until you 
        # get an error.
        # https://stackoverflow.com/questions/9901792/wmi-win32-diskdrive-to-get-total-sector-on-the-physical-disk-drive#28709238
        print('\nDone reading the reported sectors.')
        print('Now attempting to read the unreported sectors by Windows.')
        unreported = 0
        while True:
            try:
                buffer = os.read(disk_fh, sector_len)
                unreported += 1
                dest_fh.write(buffer)
            except PermissionError:
                break
        print(" `-> %d unreported sectors found" % unreported)
        print("Total sectors = %d" % (sector_total + unreported))
        print("Total bytes written = %d" % 
                                    (sector_len * (sector_total + unreported)))
        dest_fh.flush()

    os.close(disk_fh)

def get_physical_devices():
    command = "wmic diskdrive get DeviceId,TotalSectors,BytesPerSector,Model,InterfaceType"
    wmi_lines = subprocess.check_output(command).decode('cp1252').split('\r\n')
    physical_devices = []

    for line in wmi_lines[1:]:
        capture = re.search(r'(\d+)\s+(\\\\.\\[\w\d]+)\s+(\w+)\s+([\w\d][\w\d\s]*?)\s+(\d+)', line)
        if capture:
            bytes_per_sector, device_id, interface_type, model, total_sectors = capture.groups()
            physical_device = PhysicalDevice(int(bytes_per_sector), device_id, interface_type, model, int(total_sectors))
            physical_devices.append(physical_device)
    
    return physical_devices

if __name__ == "__main__":
    if os.name != 'nt':
        sys.stderr.write('Windows only, sorry.\n')
        sys.exit(1);

    ph_devices = get_physical_devices()

    # Filter out the non-USB devices to avoid accidents (for now)
    ph_devices = list(filter(
        lambda ph_dev: ph_dev.interface_type == 'USB', ph_devices))

    if len(ph_devices) == 0:
        print('No devices found to copy.')
        sys.exit(1)
    
    print('-' * 80)
    print('DEVICES LIST')
    for index,ph_device in enumerate(ph_devices):
        print(f'({index}) [{ph_device.interface_type}] ' + 
                       f'{ph_device.device_id}\t{ph_device.model}')
    answer = input('Pease select a device to image. [q to quit] ')
    try:
        ph_device_to_image = ph_devices[int(answer)]
    except:
        print('Failed to select a device. Exiting ...')
        sys.exit(1)
    
    image_destination = os.path.join(os.getcwd(), 
                                    ph_device.model.replace(' ', '') + '.copy')
    print(f"\nWriting the device {ph_device_to_image.device_id}" + 
                                         f" to the file {image_destination}\n")
    sleep(3) # Sleep for 3 seconds to allow for panic Ctrl+C exits
    dd(ph_device_to_image, image_destination)

import subprocess
import re
import pyudev
import psutil
import os
from prettytable import PrettyTable, PLAIN_COLUMNS


parted = PrettyTable(padding_width=0, left_padding_width=0, right_padding_width=0)
#x.set_style(border=False)
parted.set_style(style=PLAIN_COLUMNS)
parted.align = "l"

bay = PrettyTable()
bay.set_style(style=PLAIN_COLUMNS)
bay.align = "l"

diskspeed = PrettyTable()
diskspeed.set_style(style=PLAIN_COLUMNS)
diskspeed.align = "l"


def get_physical_block_devices():
    try:
        output = subprocess.check_output(['lsscsi', '-s'], universal_newlines=True)
        lines = output.strip().split('\n')

        # Extract specific details from each line using regex to split by multiple spaces
        devices_info = []
        for line in lines:
            parts = re.split(r'\s{2,}', line.strip())  # Split by multiple spaces
            if len(parts) >= 7 and parts[1] == 'disk':
                connected_port = parts[0].strip('[]')
                device_type = parts[1]
                device_path = parts[-2]
                size = parts[-1]
                devices_info.append((connected_port, device_type, device_path, size))

        return devices_info
    except subprocess.CalledProcessError as e:
        print(f"Error executing lsscsi: {e}")
        print("Install if needed by apt install lsscsi")
        return []


def get_vendor_and_serial(device):
    context = pyudev.Context()
    udev_device = pyudev.Devices.from_device_file(context, device)

    if udev_device.get('ID_TYPE') == 'disk':
        vendor = udev_device.get('ID_VENDOR')
        if vendor is None: vendor = ''
        serial = udev_device.get('ID_SERIAL_SHORT')
        if serial is None: vendor = ''
        return vendor, serial
    else:
        return None, None


def get_disk_speed(device):
    try:
        output = subprocess.check_output(['hdparm', '-t', device], universal_newlines=True)
        # Extracting speed using regular expression
        match = re.search(r'= +(\d+(\.\d+)?) MB/sec', output)
        if match:
            speed = match.group(1)
            return speed
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error running hdparm: {e}")
        print("Are you root?")
        return None


def get_partitions(device):
    partitions = []
    context = pyudev.Context()
    udev_device = pyudev.Devices.from_device_file(context, device)

    # Check if the provided device is a block device
    if udev_device.get('DEVTYPE') == 'disk':
        for partition in udev_device.children:
            partitions.append(partition.device_node)
    
    return partitions

def get_partition_uuid(partition):
    context = pyudev.Context()
    udev_device = pyudev.Devices.from_device_file(context, partition)

    # Check if the provided partition device is a block device
    if udev_device.get('DEVTYPE') == 'partition':
        uuid = udev_device.get('ID_FS_UUID')
        if uuid == None: return ''
        return "UUID=" + str(uuid)
    
    return None


def get_partition_fstype(partition):
    context = pyudev.Context()
    udev_device = pyudev.Devices.from_device_file(context, partition)

    # Check if the provided partition device is a block device
    if udev_device.get('DEVTYPE') == 'partition':
        fstype = udev_device.get('ID_FS_TYPE')
        if fstype == None: fstype = ''
        return fstype
    
    return None


def _get_partition_size(partition):
    try:
        partition_usage = psutil.disk_usage(partition)
        print(f'{partition_usage=}')
        size_gb = partition_usage.total / (1024 ** 3)  # Convert bytes to gigabytes
        return size_gb
    except Exception as e:
        print(f"Error retrieving partition size: {e}")
        return None


def __get_partition_size(partition):
    try:
        total_size = os.statvfs(partition).f_frsize * os.statvfs(partition).f_blocks
        size_gb = total_size / (1024 ** 3)  # Convert bytes to gigabytes
        return size_gb
    except Exception as e:
        print(f"Error retrieving partition size: {e}")
        return None

# def get_partition_size(partition):
#     try:
#         df_output = subprocess.check_output(['df', '-h', partition], universal_newlines=True)
#         lines = df_output.strip().split('\n')
#         if len(lines) > 1:
#             size = lines[1].split()[1]
#             #size_gb = int(size) / (1024 ** 3)  # Convert bytes to gigabytes
#             return size
#         else:
#             return ""
#     except subprocess.CalledProcessError as e:
#         print(f"Error retrieving partition size: {e}")
#         return None

# def get_partition_size(partition):
#     try:
#         cmd = f"df -h {partition} | grep {partition} | awk ' {{print $2}}'"  # Use awk to extract the size (field 2) from the second line
#         size_output = subprocess.check_output(cmd, shell=True, universal_newlines=True)
#         size = size_output.strip()
#         return size
#     except subprocess.CalledProcessError as e:
#         print(f"Error retrieving partition size: {e}")
#         return None

def get_partition_size(partition):
    try:
        # Run lsblk command to get information about the partition
        lsblk_output = subprocess.check_output(['lsblk', '-n', '-o', 'SIZE,FSTYPE', partition], universal_newlines=True)
        lines = lsblk_output.strip().split('\n')

        if len(lines) > 0:
            # Extract size and filesystem type (FSTYPE) from lsblk output
            info = lines[0].split()
            if len(info) == 2:
                size = info[0]
                # fstype = info[1]
                return size #, fstype
        else:
            return None #, None
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving partition info: {e}")
        return None #, None


def get_disk_usage(partition):
    try:
        # Run 'df -h' command to get disk usage information
        output = subprocess.check_output(['df', '-h', partition], universal_newlines=True)

        # Split the output by lines and extract the relevant details
        lines = output.split('\n')
        if len(lines) > 1:
            # Extract disk usage percentage and mount point
            fields = lines[1].split()
            if len(fields) >= 5:
                usage_percent = fields[4]
                mount_point = fields[-1]
                if mount_point == '/dev':
                    mount_point = ''    
                return usage_percent, mount_point
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving disk usage: {e}")
    return None, None


def print_dev_info(dev_list, partition=True, speed=False):
    bay.field_names = ["Port", "Type", "Device", "Size", "Vendor", "Serial"] 
    diskspeed.field_names = ["Port", "Type", "Device", "Size", "Vendor", "Serial", 'Read speed'] 
    parted.field_names = ["Device", "Partition", "FS", "Size", "Usage", "Mounted", "Serial/UUID"] 
    # partition_table.field_names = ["Port", "Type", "Device", "Partition", "FS", "Size(usage)", "Mounted", "Vendor", "Serial/UUID"] 
    for device_info in physical_block_devices:
        port, device_type, device_path, size = device_info
        vendor, serial = get_vendor_and_serial(device_path)
        if speed:    
            # if False:    
            #print(f"Port: {port}\t Type: {device_type}\t Device: {device_path}\t Size: {size} {vendor} {serial}\tRead speed: {get_disk_speed(device_path)} Mbit/s")
            # x.add_row([port, device_type, device_path, size, vendor,serial, f'{get_disk_speed(device_path)} Mbit/s'])
            diskspeed.add_row([port, device_type, device_path, size, vendor, serial, f'{get_disk_speed(device_path)} Mbit/s'])
        else:    
            bay.add_row([port, device_type, device_path, size, vendor, serial])
        partition_list = get_partitions(device_path)
        if partition:
            parted.add_row([device_path, "", "", size, "", "", ""])
            for partition in partition_list:
                usage_percent, mount_point = get_disk_usage(partition)
                # print(f'\t{partition}\t{get_partition_fstype(partition)}\t{get_partition_size(partition)}\t{usage_percent}\t{mount_point}\t{get_partition_uuid(partition)}')
                # x.add_row([port, device_type, device_path, size, vendor, serial])
                # x.field_names = ["Port", "Type", "Device type", "Device", "Partition", "FS", "Size", "Vendor", "Serial", "Read speed"] 
                parted.add_row(["", partition, get_partition_fstype(partition), get_partition_size(partition), usage_percent, mount_point, get_partition_uuid(partition)])

    print("List of Physical Block Devices:")
    print(bay)
    bay.clear()
    if partition:
        print(parted)
        parted.clear()
    if speed:
        print(diskspeed)
        diskspeed.clear()


if __name__ == '__main__':
    physical_block_devices = get_physical_block_devices()
    # print_dev_info(physical_block_devices, partition=False)
    # print()
    print_dev_info(physical_block_devices, partition=True)
    # print()
    print_dev_info(physical_block_devices, partition=False, speed=True)



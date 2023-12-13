import subprocess
import re
import pyudev
import psutil
import os


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
        serial = udev_device.get('ID_SERIAL_SHORT')
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
        return uuid
    
    return None


def get_partition_fstype(partition):
    context = pyudev.Context()
    udev_device = pyudev.Devices.from_device_file(context, partition)

    # Check if the provided partition device is a block device
    if udev_device.get('DEVTYPE') == 'partition':
        fstype = udev_device.get('ID_FS_TYPE')
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

def get_partition_size(partition):
    try:
        df_output = subprocess.check_output(['df', '-h', partition], universal_newlines=True)
        lines = df_output.strip().split('\n')
        if len(lines) > 1:
            size = lines[1].split()[1]
            #size_gb = int(size) / (1024 ** 3)  # Convert bytes to gigabytes
            return size
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving partition size: {e}")
        return None


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
	print("List of Physical Block Devices:")
	for device_info in physical_block_devices:
		port, device_type, device_path, size = device_info
		vendor, serial = get_vendor_and_serial(device_path)
		if speed:	
			print(f"Port: {port}\t Type: {device_type}\t Device: {device_path}\t Size: {size} {vendor} {serial}\tRead speed: {get_disk_speed(device_path)} Mbit/s")
		else:	
			print(f"Port: {port}\t Type: {device_type}\t Device: {device_path}\t Size: {size} {vendor} {serial}")
		partition_list = get_partitions(device_path)
		if partition:
			for partition in partition_list:
				usage_percent, mount_point = get_disk_usage(partition)
				print(f'\t{partition}\t{get_partition_fstype(partition)}\t{get_partition_size(partition)}\t{usage_percent}\t{mount_point}\t{get_partition_uuid(partition)}')


if __name__ == '__main__':

	physical_block_devices = get_physical_block_devices()
	print_dev_info(physical_block_devices, partition=False)
	print()
	print_dev_info(physical_block_devices, partition=True)
	print()
	print_dev_info(physical_block_devices, partition=False, speed=True)



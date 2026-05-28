#!/usr/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run this script with sudo.${NC}"
  exit 1
fi

echo -e "${GREEN}--- NAS Drive Formatter & Labeler ---${NC}"
echo -e "Available Physical Drives:"
# Lists physical disks, hiding loopbacks and tiny boot partitions
lsblk -d -n -o NAME,SIZE,MODEL | awk '$1 ~ /sd|nvme/ {print "  /dev/" $0}'
echo "----------------------------------------"

read -p "Enter the exact drive path to format (e.g., /dev/sdc): " DRIVE_PATH

# Safety check: Ensure the drive exists
if [ ! -b "$DRIVE_PATH" ]; then
    echo -e "${RED}Error: Drive $DRIVE_PATH does not exist.${NC}"
    exit 1
fi

# Safety check: Ensure they aren't trying to format the OS drive
if lsblk -n -o MOUNTPOINT "$DRIVE_PATH" | grep -q "/"; then
    echo -e "${RED}CRITICAL ERROR: $DRIVE_PATH contains your active operating system. Aborting!${NC}"
    exit 1
fi

read -p "Enter the new Label for this drive (e.g., Rex): " DRIVE_LABEL
read -p "Choose File System [1 for NTFS (Windows-compatible), 2 for Ext4 (Linux Native)]: " FS_CHOICE

echo -e "\n${RED}!!! WARNING !!!${NC}"
echo -e "You are about to COMPLETELY ERASE all data on ${YELLOW}$DRIVE_PATH${NC}."
read -p "Are you absolutely sure? Type 'YES' in all caps to proceed: " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Aborted. No changes were made."
    exit 0
fi

echo "Wiping existing partition tables..."
wipefs -a "$DRIVE_PATH" > /dev/null 2>&1

echo "Creating new GPT partition table..."
parted -s "$DRIVE_PATH" mklabel gpt
parted -s "$DRIVE_PATH" mkpart primary 0% 100%

# Wait a second for the OS to register the new partition (usually adds a '1' or 'p1' to the end)
sleep 2
if [[ "$DRIVE_PATH" == *nvme* ]]; then
    PARTITION="${DRIVE_PATH}p1"
else
    PARTITION="${DRIVE_PATH}1"
fi

if [ "$FS_CHOICE" == "1" ]; then
    echo "Formatting as NTFS with label '$DRIVE_LABEL'..."
    mkfs.ntfs -f -L "$DRIVE_LABEL" "$PARTITION"
elif [ "$FS_CHOICE" == "2" ]; then
    echo "Formatting as Ext4 with label '$DRIVE_LABEL'..."
    mkfs.ext4 -L "$DRIVE_LABEL" "$PARTITION"
else
    echo -e "${RED}Invalid choice. Aborting.${NC}"
    exit 1
fi

echo -e "${GREEN}Success! $PARTITION has been formatted and labeled as $DRIVE_LABEL.${NC}"
echo -e "You can now run your ${YELLOW}sudo ./mount-nas-drive.sh${NC} script to mount it!"

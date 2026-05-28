#!/usr/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Ensure root privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run this script with sudo.${NC}"
  exit 1
fi

echo -e "${GREEN}--- Selective DAS Disconnect (Multi-Unmount) ---${NC}"
read -p "Enter Drive Labels to take offline (comma-separated, e.g., Dogma, Karma): " INPUT_LABELS

if [ -z "$INPUT_LABELS" ]; then
  echo -e "${RED}Error: Input cannot be empty.${NC}"
  exit 1
fi

# 2. Stop Samba once to release network locks for all targeted drives
echo -e "\n${YELLOW}Stopping Samba to release network locks...${NC}"
systemctl stop smbd

# Split the input and loop
IFS=',' read -ra ADDR <<< "$INPUT_LABELS"

for DRIVE_LABEL in "${ADDR[@]}"; do
    # Clean up whitespace
    DRIVE_LABEL=$(echo "$DRIVE_LABEL" | xargs)
    DIR_NAME=$(echo "$DRIVE_LABEL" | tr '[:upper:]' '[:lower:]')
    MOUNT_POINT="/mnt/$DIR_NAME"

    echo -e "\n${YELLOW}Processing $DRIVE_LABEL...${NC}"

    # Check if it is actually mounted
    if ! mountpoint -q "$MOUNT_POINT"; then
        echo -e "${RED}Skipping: $MOUNT_POINT is not currently mounted.${NC}"
        continue
    fi

    # 3. Sync and Unmount
    echo "Syncing data and unmounting $MOUNT_POINT..."
    sync
    
    # Using lazy unmount (-l) to handle any stubborn local processes
    if umount -l "$MOUNT_POINT"; then
        echo -e "${GREEN}Success: $DRIVE_LABEL has been unmounted.${NC}"
    else
        echo -e "${RED}Failed to unmount $DRIVE_LABEL.${NC}"
    fi
done

# 4. Restart Samba for the remaining drives in the fleet
echo -e "\n${YELLOW}Restarting Samba for remaining shares...${NC}"
systemctl start smbd

echo -e "\n${GREEN}DONE:${NC} You can now safely power down the DAS for the processed drives."
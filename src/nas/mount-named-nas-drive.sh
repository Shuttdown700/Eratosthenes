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

echo -e "${GREEN}--- NAS Drive Automounter ---${NC}"
read -p "Enter the exact Windows drive label (e.g., Gree): " DRIVE_LABEL

if [ -z "$DRIVE_LABEL" ]; then
  echo -e "${RED}Error: Label cannot be empty.${NC}"
  exit 1
fi

# 2. Extract UUID and File System Type using blkid
UUID=$(blkid -t LABEL="$DRIVE_LABEL" -s UUID -o value)
FSTYPE=$(blkid -t LABEL="$DRIVE_LABEL" -s TYPE -o value)

if [ -z "$UUID" ]; then
  echo -e "${RED}Error: Could not find a plugged-in drive with the label '$DRIVE_LABEL'. Check connections.${NC}"
  exit 1
fi

# 3. Convert label to lowercase for the Linux mount point
DIR_NAME=$(echo "$DRIVE_LABEL" | tr '[:upper:]' '[:lower:]')
MOUNT_POINT="/mnt/$DIR_NAME"

echo -e "\nFound Drive: ${YELLOW}$DRIVE_LABEL${NC} (UUID: $UUID, Type: $FSTYPE)"
echo -e "Target Mount Point: ${YELLOW}$MOUNT_POINT${NC}\n"

# 4. Prevent duplicate entries in fstab
if grep -q "$UUID" /etc/fstab; then
  echo -e "${YELLOW}Warning: This drive is already configured in /etc/fstab! Aborting to prevent duplicates.${NC}"
  exit 1
fi

# 5. Create the directory
mkdir -p "$MOUNT_POINT"

# 6. Determine mount options (Optimized for Windows NTFS media drives)
if [[ "$FSTYPE" == "ntfs" ]]; then
    ACTUAL_FSTYPE="ntfs3"
    OPTIONS="defaults,uid=1000,gid=1000,umask=022,nofail"
else
    # Fallback for Linux native drives (ext4, etc.)
    ACTUAL_FSTYPE="$FSTYPE"
    OPTIONS="defaults,nofail"
fi

# 7. Write to fstab
echo "" >> /etc/fstab
echo "# Drive: $DRIVE_LABEL added via automount script" >> /etc/fstab
echo "UUID=$UUID $MOUNT_POINT $ACTUAL_FSTYPE $OPTIONS 0 0" >> /etc/fstab

# 8. Reload and Mount
echo "Reloading systemd and mounting..."
systemctl daemon-reload
mount -a

echo -e "${GREEN}Success! Drive is permanently mounted.${NC}"
echo "Here are the contents of $MOUNT_POINT:"
ls -la "$MOUNT_POINT" | head -n 10

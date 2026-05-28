#!/usr/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Editing Samba configurations requires sudo.${NC}"
  exit 1
fi

echo -e "${GREEN}--- NAS Network Share (Samba) Automator ---${NC}"
read -p "Enter the exact Drive/Share Name (e.g., Rex, Appo): " SHARE_NAME

if [ -z "$SHARE_NAME" ]; then
  echo -e "${RED}Error: Share Name cannot be empty.${NC}"
  exit 1
fi

# Convert the label to lowercase to match your mount paths (e.g., /mnt/rex)
DIR_NAME=$(echo "$SHARE_NAME" | tr '[:upper:]' '[:lower:]')
MOUNT_POINT="/mnt/$DIR_NAME"

# Default to eratosthenes if you just press Enter
read -p "Enter the authorized Linux user [Default: eratosthenes]: " SMB_USER
SMB_USER=${SMB_USER:-eratosthenes}

# 1. Safety Check: Does the folder actually exist?
if [ ! -d "$MOUNT_POINT" ]; then
  echo -e "${YELLOW}Warning: The mount path $MOUNT_POINT does not exist.${NC}"
  echo "Please make sure you have run your mount script first!"
  exit 1
fi

# 2. Safety Check: Does this share already exist in the file?
if grep -q -i "\[$SHARE_NAME\]" /etc/samba/smb.conf; then
  echo -e "${RED}Error: A network share named [$SHARE_NAME] is already configured in /etc/samba/smb.conf! Aborting to prevent duplicates.${NC}"
  exit 1
fi

echo "Injecting [$SHARE_NAME] configuration into /etc/samba/smb.conf..."

# 3. Append the configuration block to the very bottom of the file
cat <<EOF >> /etc/samba/smb.conf

[$SHARE_NAME]
comment = $SHARE_NAME Media Drive
path = $MOUNT_POINT
valid users = $SMB_USER
read only = no
guest ok = no
create mask = 0775
directory mask = 0775
EOF

# 4. Restart the service to apply changes instantly
echo "Restarting Samba service..."
systemctl restart smbd

echo -e "${GREEN}Success! The drive is now broadcasting to your network.${NC}"
echo -e "You can access it on your Windows machine at: ${YELLOW}\\\\10.0.0.213\\$SHARE_NAME${NC}"

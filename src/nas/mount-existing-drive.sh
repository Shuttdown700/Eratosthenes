#!/usr/bin/bash

# Define Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}--- NAS Trooper Deployment (Auto-Repair Mode) ---${NC}"
read -p "Enter Drive Labels (comma-separated, or type 'ALL'): " INPUT_LABELS

RESTART_SAMBA=false

# Deployment Logic: Handle 'ALL' or specific labels
if [[ "${INPUT_LABELS^^}" == "ALL" ]]; then
    # Scrapes /etc/fstab for any mount points in /mnt/ to build the fleet list
    DRIVE_LIST=($(grep "[[:space:]]/mnt/" /etc/fstab | awk '{print $2}' | sed 's/\/mnt\///'))
else
    IFS=',' read -ra DRIVE_LIST <<< "$INPUT_LABELS"
fi

for DRIVE_LABEL in "${DRIVE_LIST[@]}"; do
    # Cleanup label string
    DRIVE_LABEL=$(echo "$DRIVE_LABEL" | xargs)
    DIR_NAME=$(echo "$DRIVE_LABEL" | tr '[:upper:]' '[:lower:]')
    MOUNT_POINT="/mnt/$DIR_NAME"

    echo -e "\n${YELLOW}Processing $DRIVE_LABEL...${NC}"

    # Check if the mount directory actually exists
    if [ ! -d "$MOUNT_POINT" ]; then
        echo -e "${RED}Error: Mount point $MOUNT_POINT does not exist in the filesystem.${NC}"
        continue
    fi

    # Skip if already mounted
    if mountpoint -q "$MOUNT_POINT"; then
        echo -e "${YELLOW}$DRIVE_LABEL is already online.${NC}"
        continue
    fi

    # Attempt standard mount
    sudo mount "$MOUNT_POINT" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Success! $DRIVE_LABEL is back in the fleet.${NC}"
        RESTART_SAMBA=true
    else
        echo -e "${YELLOW}Standard mount failed. Resolving device for repair...${NC}"
        
        # 1. Get the identifier (UUID, LABEL, or /dev/ path) from fstab
        FSTAB_ID=$(grep "[[:space:]]$MOUNT_POINT[[:space:]]" /etc/fstab | awk '{print $1}')

        if [[ -z "$FSTAB_ID" ]]; then
            echo -e "${RED}Error: No fstab entry found for $MOUNT_POINT.${NC}"
            continue
        fi

        # 2. Resolve the ID to a real /dev/ node (handles UUID=... and LABEL=...)
        REAL_DEV=$(blkid -o device -t "$FSTAB_ID" | head -n 1)

        # 3. Fallback if fstab uses a direct /dev/ path
        if [[ -z "$REAL_DEV" && "$FSTAB_ID" == /dev/* ]]; then
            REAL_DEV="$FSTAB_ID"
        fi

        if [[ -z "$REAL_DEV" ]]; then
            echo -e "${RED}Error: Could not find hardware device for $FSTAB_ID.${NC}"
            continue
        fi

        # 4. Perform the repair on the REAL device path
        echo -e "${YELLOW}Running repair on $REAL_DEV...${NC}"
        sudo ntfsfix -d "$REAL_DEV"
        
        # 5. Final mount attempt
        sudo mount "$MOUNT_POINT"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Repair Successful! $DRIVE_LABEL is back online.${NC}"
            RESTART_SAMBA=true
        else
            echo -e "${RED}Deployment Failed. Check dmesg for hardware issues on $DRIVE_LABEL.${NC}"
        fi
    fi
done

# Restart Samba only if at least one drive was successfully mounted
if [ "$RESTART_SAMBA" = true ]; then
    echo -e "\n${GREEN}Refreshing Samba services...${NC}"
    sudo systemctl restart smbd
    echo -e "${GREEN}All systems operational.${NC}"
fi
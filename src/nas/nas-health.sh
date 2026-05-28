#!/usr/bin/bash

# Define Colors for the UI
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ensure the script is run as root (required for SMART data)
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Drive health requires root access. Please run with 'sudo ./nas-health.sh'${NC}"
  exit 1
fi

echo -e "\n========================================="
echo -e "  NAS HEALTH ASSESSMENT & INSIGHTS"
echo -e "=========================================\n"

read -p "Press [Enter] to begin system diagnostics..."

# Ask upfront whether to run the fragmentation check
echo ""
read -p "Run fragmentation check on mounted drives? This may take several minutes. [y/N]: " FRAG_CHOICE
case "$FRAG_CHOICE" in
  [yY][eE][sS]|[yY]) RUN_FRAG=true ;;
  *) RUN_FRAG=false ;;
esac

# Arrays and counters to hold our final assessment data
INSIGHTS=()
WARNINGS=0

# Associative array to store frag results per drive for the final summary
declare -A FRAG_RESULTS

echo -e "\n--- 1. CPU & MEMORY ---"
# Calculate Memory Usage
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
USED_RAM=$(free -m | awk '/^Mem:/{print $3}')
RAM_PCT=$((USED_RAM * 100 / TOTAL_RAM))

echo -n "Memory Usage: $USED_RAM MB / $TOTAL_RAM MB ($RAM_PCT%) - "
if [ "$RAM_PCT" -lt 80 ]; then
    echo -e "${GREEN}Healthy${NC}"
else
    echo -e "${YELLOW}High${NC}"
    INSIGHTS+=("Memory usage is at ${RAM_PCT}%. Keep an eye on Docker container limits.")
    ((WARNINGS++))
fi

# Get CPU Load Average (1 minute)
CPU_LOAD=$(uptime | awk -F'load average:' '{ print $2 }' | cut -d, -f1 | xargs)
echo -e "CPU Load (1m avg): $CPU_LOAD"

echo -e "\n--- 2. THERMALS ---"
# Parse lm-sensors for the absolute highest live temperature recorded
if command -v sensors &> /dev/null; then
    MAX_TEMP=$(sensors | awk -F':' '/:/ {print $2}' | awk '{print $1}' | grep -Eo '[0-9]+\.[0-9]' | awk '{print int($1)}' | sort -nr | head -n1)
    
    if [ -z "$MAX_TEMP" ]; then
        echo -e "${YELLOW}Could not read temperature. Did you run 'sudo sensors-detect'?${NC}"
    else
        echo -n "Max CPU Temperature: ${MAX_TEMP}°C - "
        if [ "$MAX_TEMP" -lt 65 ]; then
            echo -e "${GREEN}Cool & Optimal${NC}"
        elif [ "$MAX_TEMP" -lt 85 ]; then
            echo -e "${YELLOW}Warm${NC}"
            INSIGHTS+=("CPU is running warm (${MAX_TEMP}°C). Monitor your ambient room temperature.")
            ((WARNINGS++))
        else
            echo -e "${RED}Critical${NC}"
            INSIGHTS+=("CPU is overheating! (${MAX_TEMP}°C). Check your Intel i5 cooler and NAS fans immediately.")
            ((WARNINGS++))
        fi
    fi
else
    echo -e "${YELLOW}lm-sensors binary not found.${NC}"
fi

echo -e "\n--- 3. DRIVE FLEET HEALTH ---"
# Dynamically find all attached physical disks (ignores partitions and virtual drives)
DRIVES=$(lsblk -d -n -o NAME,TYPE | awk '$2=="disk" {print $1}')
TOTAL_DRIVES=$(echo "$DRIVES" | wc -w)

echo -e "Total Physical Drives Online: ${CYAN}${TOTAL_DRIVES}${NC}\n"

if command -v smartctl &> /dev/null; then
    for drive in $DRIVES; do
        # 1. Grab the custom NTFS label from the drive's partitions (Ignoring EFI partitions)
        DRIVE_LABEL=$(lsblk -n -o LABEL /dev/$drive | grep -v "^$" | grep -iv "EFI" | head -n 1)
        if [ -z "$DRIVE_LABEL" ]; then
            DRIVE_LABEL="Unlabeled"
        fi

        # 2. Find where the drive is mounted to pull capacity stats
        MOUNT_POINT=$(lsblk -n -o MOUNTPOINT /dev/$drive | grep -v "^$" | grep -v "/boot" | head -n 1)

        echo -n -e "Drive /dev/$drive [${CYAN}$DRIVE_LABEL${NC}]: "
        
        # 3. Pull the specific SMART health string
        SMART_OUTPUT=$(smartctl -H /dev/$drive 2>/dev/null)
        
        if echo "$SMART_OUTPUT" | grep -iqE "PASSED|OK"; then
            echo -n -e "${GREEN}HEALTHY${NC} "
        else
            echo -n -e "${RED}FAILED${NC} "
            INSIGHTS+=("Drive /dev/$drive [$DRIVE_LABEL] failed the SMART health check.")
            ((WARNINGS++))
        fi

        # Drive Temperature Check
        DRIVE_TEMP=$(smartctl -A /dev/$drive 2>/dev/null | grep -i "Temperature_Celsius" | awk '{print $10}')
        if [ -n "$DRIVE_TEMP" ]; then
            if [ "$DRIVE_TEMP" -lt 45 ]; then
                echo -n -e "[${GREEN}${DRIVE_TEMP}°C${NC}]"
            else
                echo -n -e "[${RED}${DRIVE_TEMP}°C${NC}]"
                INSIGHTS+=("Drive $DRIVE_LABEL is running hot ($DRIVE_TEMP°C).")
                ((WARNINGS++))
            fi
        else
            echo -n "[Temp: N/A]"
        fi

        # 4. Calculate capacity if the drive is actively mounted
        if [ -n "$MOUNT_POINT" ]; then
            CAP_TOTAL=$(df -h "$MOUNT_POINT" | awk 'NR==2 {print $2}')
            CAP_USED=$(df -h "$MOUNT_POINT" | awk 'NR==2 {print $3}')
            CAP_PCT=$(df -h "$MOUNT_POINT" | awk 'NR==2 {print $5}')
            PCT_NUM=$(echo "$CAP_PCT" | tr -dc '0-9')
            
            if [ -n "$PCT_NUM" ] && [ "$PCT_NUM" -ge 95 ]; then
                echo -e " | Storage: ${CAP_USED} of ${CAP_TOTAL} (${RED}${CAP_PCT}${NC})"
            else
                echo -e " | Storage: ${CAP_USED} of ${CAP_TOTAL} (${CAP_PCT})"
            fi

            # 5. Fragmentation check (only if user opted in and drive is mounted)
            if [ "$RUN_FRAG" = true ]; then
                # Detect the filesystem type for the mount point
                FS_TYPE=$(findmnt -n -o FSTYPE "$MOUNT_POINT" 2>/dev/null)
                
                case "$FS_TYPE" in
                  ext4|ext3|ext2)
                    echo -e "  +- Checking fragmentation on $MOUNT_POINT (${FS_TYPE})..."
                    # e2fsck -n is a safe, read-only dry run
                    FRAG_OUTPUT=$(e2fsck -fn "$(findmnt -n -o SOURCE "$MOUNT_POINT")" 2>&1)
                    # Pull the fragmentation percentage from the e2fsck summary line
                    FRAG_PCT=$(echo "$FRAG_OUTPUT" | grep -i "non-contiguous" | grep -Eo '[0-9]+(\.[0-9]+)?%' | head -n1)
                    
                    if [ -z "$FRAG_PCT" ]; then
                        FRAG_RESULTS[$DRIVE_LABEL]="Could not determine (check e2fsck output manually)"
                    else
                        # Strip the % and compare as integer
                        FRAG_NUM=$(echo "$FRAG_PCT" | tr -dc '0-9.')
                        FRAG_INT=$(printf "%.0f" "$FRAG_NUM")
                        
                        if [ "$FRAG_INT" -lt 5 ]; then
                            echo -e "     ${GREEN}Fragmentation: ${FRAG_PCT}  Healthy${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_PCT}  Healthy"
                        elif [ "$FRAG_INT" -lt 15 ]; then
                            echo -e "     ${YELLOW}Fragmentation: ${FRAG_PCT}  Moderate${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_PCT}  Moderate"
                            INSIGHTS+=("Drive $DRIVE_LABEL has moderate fragmentation (${FRAG_PCT}). Consider running e4defrag.")
                            ((WARNINGS++))
                        else
                            echo -e "     ${RED}Fragmentation: ${FRAG_PCT}  High${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_PCT}  High. Run: e4defrag $MOUNT_POINT"
                            INSIGHTS+=("Drive $DRIVE_LABEL has high fragmentation (${FRAG_PCT}). Run: sudo e4defrag $MOUNT_POINT")
                            ((WARNINGS++))
                        fi
                    fi
                    ;;
                  btrfs)
                    echo -e "  +- Checking fragmentation on $MOUNT_POINT (btrfs)..."
                    # btrfs fi defrag -r -c --dryrun is the read-only equivalent
                    FRAG_COUNT=$(btrfs filesystem defragment -r -c --dryrun "$MOUNT_POINT" 2>/dev/null | wc -l)
                    
                    if [ "$FRAG_COUNT" -lt 100 ]; then
                        echo -e "     ${GREEN}Fragmentation: Low (~${FRAG_COUNT} extents flagged)${NC}"
                        FRAG_RESULTS[$DRIVE_LABEL]="Low (~${FRAG_COUNT} extents flagged)"
                    elif [ "$FRAG_COUNT" -lt 1000 ]; then
                        echo -e "     ${YELLOW}Fragmentation: Moderate (~${FRAG_COUNT} extents flagged)${NC}"
                        FRAG_RESULTS[$DRIVE_LABEL]="Moderate (~${FRAG_COUNT} extents flagged)"
                        INSIGHTS+=("Drive $DRIVE_LABEL (btrfs) has moderate fragmentation (~${FRAG_COUNT} extents). Consider btrfs fi defrag.")
                        ((WARNINGS++))
                    else
                        echo -e "     ${RED}Fragmentation: High (~${FRAG_COUNT} extents flagged)${NC}"
                        FRAG_RESULTS[$DRIVE_LABEL]="High (~${FRAG_COUNT} extents flagged). Run: btrfs fi defrag -r $MOUNT_POINT"
                        INSIGHTS+=("Drive $DRIVE_LABEL (btrfs) has high fragmentation (~${FRAG_COUNT} extents). Run: sudo btrfs fi defrag -r $MOUNT_POINT")
                        ((WARNINGS++))
                    fi
                    ;;
                  xfs)
                    echo -e "  +- Checking fragmentation on $MOUNT_POINT (xfs)..."
                    # xfs_db -r is read-only; fragmentation factor is the key metric
                    FRAG_FACTOR=$(xfs_db -r -c 'frag' "$(findmnt -n -o SOURCE "$MOUNT_POINT")" 2>/dev/null | grep -i "fragmentation factor" | awk '{print $NF}' | tr -dc '0-9.')
                    
                    if [ -z "$FRAG_FACTOR" ]; then
                        echo -e "     ${YELLOW}Could not read XFS fragmentation (is xfsprogs installed?)${NC}"
                        FRAG_RESULTS[$DRIVE_LABEL]="Could not determine (check xfsprogs)"
                    else
                        FRAG_INT=$(printf "%.0f" "$FRAG_FACTOR")
                        if [ "$FRAG_INT" -lt 10 ]; then
                            echo -e "     ${GREEN}Fragmentation factor: ${FRAG_FACTOR}%  Healthy${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_FACTOR}%  Healthy"
                        elif [ "$FRAG_INT" -lt 30 ]; then
                            echo -e "     ${YELLOW}Fragmentation factor: ${FRAG_FACTOR}%  Moderate${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_FACTOR}%  Moderate"
                            INSIGHTS+=("Drive $DRIVE_LABEL (xfs) has a moderate fragmentation factor (${FRAG_FACTOR}%). Consider xfs_fsr.")
                            ((WARNINGS++))
                        else
                            echo -e "     ${RED}Fragmentation factor: ${FRAG_FACTOR}%  High${NC}"
                            FRAG_RESULTS[$DRIVE_LABEL]="${FRAG_FACTOR}%  High. Run: xfs_fsr $MOUNT_POINT"
                            INSIGHTS+=("Drive $DRIVE_LABEL (xfs) has high fragmentation (${FRAG_FACTOR}%). Run: sudo xfs_fsr $MOUNT_POINT")
                            ((WARNINGS++))
                        fi
                    fi
                    ;;
                  ntfs)
                    echo -e "  +- Skipping fragmentation check for $MOUNT_POINT (NTFS  use Windows defrag tool)"
                    FRAG_RESULTS[$DRIVE_LABEL]="Skipped (NTFS  defrag via Windows)"
                    ;;
                  *)
                    echo -e "  +- Fragmentation check not supported for filesystem type: ${FS_TYPE:-unknown}"
                    FRAG_RESULTS[$DRIVE_LABEL]="Not supported (${FS_TYPE:-unknown})"
                    ;;
                esac
            fi
        else
            echo -e " | Storage: ${YELLOW}Not Mounted${NC}"
        fi

    done
else
    echo -e "${YELLOW}smartmontools binary not found.${NC}"
fi

echo -e "\n========================================="
echo -e "  OVERALL ASSESSMENT & KEY INSIGHTS"
echo -e "=========================================\n"

# Print fragmentation summary table if the check was run
if [ "$RUN_FRAG" = true ] && [ "${#FRAG_RESULTS[@]}" -gt 0 ]; then
    echo -e "--- FRAGMENTATION SUMMARY ---"
    for label in "${!FRAG_RESULTS[@]}"; do
        printf "  %-20s %s\n" "[$label]" "${FRAG_RESULTS[$label]}"
    done
    echo ""
fi

# Final Logic Gate
if [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}STATUS: EXCELLENT${NC}"
    echo "The fleet is fully operational. Thermals are in check, RAM has headroom, and all physical drives are reporting healthy."
else
    echo -e "${RED}STATUS: NEEDS ATTENTION ($WARNINGS Warning/s)${NC}"
    for insight in "${INSIGHTS[@]}"; do
        echo -e "  * $insight"
    done
fi
echo -e "\nDiagnostics complete.\n"
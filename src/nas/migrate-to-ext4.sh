#!/usr/bin/bash
set -euo pipefail

# =============================================================================
# NTFS ? EXT4 Migration Assistant
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_section() { echo -e "\n${CYAN}${BOLD}>>> $*${NC}"; }

# -----------------------------------------------------------------------------
# Cleanup / rollback on unexpected exit
# -----------------------------------------------------------------------------
SAMBA_WAS_RUNNING=false
FSTAB_BACKED_UP=false

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Script exited unexpectedly (code $exit_code). Running cleanup..."
        if $FSTAB_BACKED_UP; then
            log_warn "Restoring /etc/fstab from backup..."
            cp /etc/fstab.bak /etc/fstab
        fi
        if $SAMBA_WAS_RUNNING; then
            log_info "Restarting Samba..."
            systemctl start smbd 2>/dev/null || true
        fi
    fi
}
trap cleanup EXIT

# -----------------------------------------------------------------------------
# 1. Root check
# -----------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    log_error "Migration requires root. Re-run with: sudo $0"
    exit 1
fi

# -----------------------------------------------------------------------------
# 2. Dependency check
# -----------------------------------------------------------------------------
log_section "Checking dependencies"
for cmd in blkid mkfs.ext4 mount umount sed systemctl partprobe; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required command not found: $cmd"
        exit 1
    fi
done
log_info "All dependencies satisfied."

# -----------------------------------------------------------------------------
# 3. Drive selection
# -----------------------------------------------------------------------------
log_section "Drive Selection"
echo ""
read -rp "Enter the exact Drive Label to REFORMAT (e.g., Appo): " DRIVE_LABEL

if [ -z "$DRIVE_LABEL" ]; then
    log_error "Label cannot be empty."
    exit 1
fi

PARTITION=$(blkid -L "$DRIVE_LABEL" 2>/dev/null || true)
if [ -z "$PARTITION" ]; then
    log_error "Could not find a drive with label '$DRIVE_LABEL'."
    log_info  "Available labels on this system:"
    blkid -o value -s LABEL | sort -u | sed 's/^/  /'
    exit 1
fi

# Derive mount point and target owner early so we can show them in the summary
DIR_NAME=$(echo "$DRIVE_LABEL" | tr '[:upper:]' '[:lower:]')
MOUNT_POINT="/mnt/$DIR_NAME"

# Resolve the block device for safety (e.g., confirm it's not the root device)
ROOT_DEV=$(findmnt -n -o SOURCE /)
if [ "$PARTITION" = "$ROOT_DEV" ]; then
    log_error "Refusing to format the root filesystem device ($PARTITION)."
    exit 1
fi

# -----------------------------------------------------------------------------
# 4. Confirm owner
# -----------------------------------------------------------------------------
read -rp "Username to own the mount point [eratosthenes]: " TARGET_USER
TARGET_USER="${TARGET_USER:-eratosthenes}"

if ! id "$TARGET_USER" &>/dev/null; then
    log_error "User '$TARGET_USER' does not exist on this system."
    exit 1
fi

# -----------------------------------------------------------------------------
# 5. Summary + final confirmation
# -----------------------------------------------------------------------------
log_section "Migration Plan"
echo -e "  Partition  : ${BOLD}$PARTITION${NC}"
echo -e "  Label      : ${BOLD}$DRIVE_LABEL${NC}"
echo -e "  Format     : ${BOLD}ext4${NC}  (reserved blocks: 1%)"
echo -e "  Mount point: ${BOLD}$MOUNT_POINT${NC}"
echo -e "  Owner      : ${BOLD}$TARGET_USER${NC}"
echo ""
log_warn "ALL DATA ON $PARTITION WILL BE PERMANENTLY DESTROYED."
echo ""
read -rp "Type 'YES' to proceed, anything else to abort: " CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    log_info "Migration aborted. Nothing was changed."
    exit 0
fi

# -----------------------------------------------------------------------------
# 6. Stop Samba and unmount
# -----------------------------------------------------------------------------
log_section "Preparing Filesystem"

if systemctl is-active --quiet smbd; then
    SAMBA_WAS_RUNNING=true
    log_info "Stopping Samba..."
    systemctl stop smbd
else
    log_info "Samba was not running  skipping stop."
fi

# Strict unmount (no lazy flag); fail loudly if something holds the device open
if findmnt "$PARTITION" &>/dev/null; then
    log_info "Unmounting $PARTITION..."
    if ! umount "$PARTITION"; then
        log_error "Could not unmount $PARTITION. Check for open files with: lsof +f -- $PARTITION"
        exit 1
    fi
else
    log_info "$PARTITION is not currently mounted  skipping unmount."
fi

# -----------------------------------------------------------------------------
# 7. Format to EXT4
# -----------------------------------------------------------------------------
log_section "Formatting"
log_warn "Formatting $PARTITION as ext4 with label '$DRIVE_LABEL'..."

if ! mkfs.ext4 -F -L "$DRIVE_LABEL" -m 1 "$PARTITION"; then
    log_error "mkfs.ext4 failed. Filesystem was NOT changed."
    exit 1
fi

log_info "Format complete."

# Give the kernel a moment to update device metadata
partprobe "$PARTITION" 2>/dev/null || true
sleep 1

# -----------------------------------------------------------------------------
# 8. Capture new UUID (with guard)
# -----------------------------------------------------------------------------
log_section "Reading New UUID"
NEW_UUID=$(blkid -s UUID -o value "$PARTITION" 2>/dev/null || true)

if [ -z "$NEW_UUID" ]; then
    log_error "Could not read UUID from $PARTITION after formatting."
    log_error "The format succeeded, but fstab was NOT updated."
    log_error "You must manually add an entry to /etc/fstab."
    exit 1
fi

log_info "New UUID: $NEW_UUID"

# -----------------------------------------------------------------------------
# 9. Update fstab
# -----------------------------------------------------------------------------
log_section "Updating /etc/fstab"

cp /etc/fstab /etc/fstab.bak
FSTAB_BACKED_UP=true
log_info "Backed up /etc/fstab ? /etc/fstab.bak"

# Remove old entries for this mount point, anchoring match to the second field
# to prevent /mnt/appo from also deleting /mnt/appo2
sed -i "\| $MOUNT_POINT |d" /etc/fstab

echo "UUID=$NEW_UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
log_info "fstab entry written."

# Verify the new entry looks sane (basic sanity, not full parse)
if ! grep -q "$NEW_UUID" /etc/fstab; then
    log_error "fstab verification failed  UUID not found after write."
    exit 1
fi

# -----------------------------------------------------------------------------
# 10. Mount and set permissions
# -----------------------------------------------------------------------------
log_section "Mounting and Setting Permissions"

systemctl daemon-reload
mkdir -p "$MOUNT_POINT"

if ! mount "$MOUNT_POINT"; then
    log_error "Mount failed. Check the fstab entry:"
    grep "$NEW_UUID" /etc/fstab
    exit 1
fi

log_info "Mounted at $MOUNT_POINT"

chown "$TARGET_USER":"$TARGET_USER" "$MOUNT_POINT"
chmod 755 "$MOUNT_POINT"
log_info "Ownership set to $TARGET_USER:$TARGET_USER, permissions 755."

# -----------------------------------------------------------------------------
# 11. Restore Samba
# -----------------------------------------------------------------------------
if $SAMBA_WAS_RUNNING; then
    log_section "Restoring Samba"
    systemctl start smbd
    log_info "Samba restarted."
fi

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
log_section "Migration Complete"
echo -e "${GREEN}${BOLD}$DRIVE_LABEL is now ext4 and mounted at $MOUNT_POINT${NC}"
echo ""
echo "Mount details:"
findmnt "$MOUNT_POINT"
echo ""
echo "Disk usage:"
df -h "$MOUNT_POINT"
#!/bin/bash
set -euxo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
CODE=$(tr -d '\r\n ' < "$HERE/tv-code.txt")
WORK=${WORK:-$HERE/../work}
mkdir -p "$WORK"; cd "$WORK"
curl -fsSL -o rpi.img.xz https://downloads.raspberrypi.com/raspios_lite_arm64_latest
xz -d -T0 rpi.img.xz
IMG=$WORK/rpi.img
truncate -s +2G "$IMG"
sudo parted -s "$IMG" resizepart 2 100%
LOOP=$(sudo losetup -fP --show "$IMG")
sudo e2fsck -fy "${LOOP}p2" || true
sudo resize2fs "${LOOP}p2"
R=$WORK/root
sudo mkdir -p "$R"
sudo mount "${LOOP}p2" "$R"
sudo mount "${LOOP}p1" "$R/boot/firmware"
sudo mount -t proc proc "$R/proc"
sudo mount --bind /sys "$R/sys"
sudo mount --bind /dev "$R/dev"
sudo mount --bind /dev/pts "$R/dev/pts"
sudo cp -a "$R/etc/resolv.conf" "$WORK/resolv.conf.orig" 2>/dev/null || true
sudo rm -f "$R/etc/resolv.conf"
sudo cp /etc/resolv.conf "$R/etc/resolv.conf"
sudo cp /usr/bin/qemu-aarch64-static "$R/usr/bin/" || true
C() { sudo chroot "$R" /usr/bin/env DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 /bin/bash -c "$1"; }
C "apt-get update"
C "apt-get install -y --no-install-recommends cage chromium fonts-dejavu-core curl ca-certificates alsa-utils swh-plugins iw rfkill || apt-get install -y --no-install-recommends cage chromium-browser fonts-dejavu-core curl ca-certificates alsa-utils swh-plugins iw rfkill"
C "sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT=\"us\"/' /etc/default/keyboard 2>/dev/null || true"
C "ln -sf /usr/share/zoneinfo/America/Chicago /etc/localtime && echo America/Chicago > /etc/timezone"
C "id tv >/dev/null 2>&1 || useradd -m -s /bin/bash -G video,render,input,audio,netdev tv; passwd -l tv"
C "systemctl mask userconfig.service >/dev/null 2>&1 || true; rm -f /etc/systemd/system/multi-user.target.wants/userconfig.service"
sudo install -m 0755 "$HERE/files/retrotv-kiosk" "$R/usr/local/bin/retrotv-kiosk"
sudo install -m 0755 "$HERE/files/retrotv-wifi" "$R/usr/local/bin/retrotv-wifi"
sudo install -m 0755 "$HERE/files/retrotv-status" "$R/usr/local/bin/retrotv-status"
for d in chromium chromium-browser; do sudo mkdir -p "$R/etc/$d/policies/managed"; sudo install -m 0644 "$HERE/files/chromium-policy.json" "$R/etc/$d/policies/managed/retrotv.json"; done
sudo mkdir -p "$R/etc/retrotv"; date -u +%Y-%m-%d | sudo tee "$R/etc/retrotv/version" >/dev/null
for u in retrotv.service retrotv-wifi.service retrotv-status.service retrotv-restart.service retrotv-restart.timer; do sudo install -m 0644 "$HERE/files/$u" "$R/etc/systemd/system/$u"; done
sudo install -m 0644 "$HERE/files/pam-cage" "$R/etc/pam.d/cage"
sudo install -m 0644 "$HERE/files/asound.conf" "$R/etc/asound.conf"
test -f "$R/usr/lib/ladspa/sc4_1882.so" && test -f "$R/usr/lib/ladspa/fast_lookahead_limiter_1913.so" && test -f "$R/usr/lib/ladspa/notch_iir_1894.so" && test -f "$R/usr/lib/ladspa/highpass_iir_1890.so"
sudo mkdir -p "$R/etc/retrotv"
echo "$CODE" | sudo tee "$R/etc/retrotv/tv-code" >/dev/null
for f in retrotv-wifi.txt retrotv-settings.txt retrotv-README.txt; do sudo install -m 0644 "$HERE/files/$f" "$R/boot/firmware/$f"; done
echo retrotv | sudo tee "$R/etc/hostname" >/dev/null
sudo sed -i 's/raspberrypi/retrotv/g' "$R/etc/hosts"
C "systemctl enable retrotv.service retrotv-wifi.service retrotv-status.service retrotv-restart.timer; systemctl set-default graphical.target; systemctl disable getty@tty1.service || true"
CFG="$R/boot/firmware/config.txt"
sudo sed -i 's/^dtoverlay=vc4-kms-v3d.*/dtoverlay=vc4-kms-v3d,composite/' "$CFG"
grep -q '^dtoverlay=vc4-kms-v3d,composite' "$CFG" || echo 'dtoverlay=vc4-kms-v3d,composite' | sudo tee -a "$CFG" >/dev/null
printf '\n[pi4]\nenable_tvout=1\n\n[all]\ndtparam=audio=on\ndtoverlay=gpio-fan,gpiopin=14,temp=60000\n' | sudo tee -a "$CFG" >/dev/null
CMD="$R/boot/firmware/cmdline.txt"
sudo sed -i '1 s/$/ video=Composite-1:720x480@60ie consoleblank=0 vt.global_cursor_default=0 logo.nologo/' "$CMD"
cat "$CFG" "$CMD"
C "apt-get clean; rm -rf /var/lib/apt/lists/*"
sudo rm -f "$R/usr/bin/qemu-aarch64-static" "$R/etc/resolv.conf"
if [ -e "$WORK/resolv.conf.orig" ] || [ -L "$WORK/resolv.conf.orig" ]; then sudo cp -a "$WORK/resolv.conf.orig" "$R/etc/resolv.conf"; fi
sudo umount "$R/dev/pts" "$R/dev" "$R/sys" "$R/proc" "$R/boot/firmware" "$R"
sudo zerofree "${LOOP}p2" || true
sudo losetup -d "$LOOP"
mv "$IMG" "$WORK/retrotv-pi.img"
xz -T0 -6 -v "$WORK/retrotv-pi.img"
ls -la "$WORK"

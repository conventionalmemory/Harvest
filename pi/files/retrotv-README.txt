RETRO TV FOR RASPBERRY PI

1. Set up Wi-Fi in Raspberry Pi Imager's options when you write the card, or
   open network-config on this card and add your Wi-Fi at the bottom, using
   spaces only, no tabs:
   network:
     version: 2
     wifis:
       wlan0:
         dhcp4: true
         optional: true
         regulatory-domain: US
         access-points:
           "YourNetworkName":
             password: "YourPassword"
2. Put the card in the Pi. Plug the Pi's composite video (the 3.5mm AV jack on a
   Pi 3 or Pi 4, using a TRRS-to-RCA cable) into the TV's yellow video input
   and the audio into the white/red inputs.
3. Power on. The Pi joins your Wi-Fi and opens straight to the cable guide.
4. Scan the QR code on your printed remote card with your phone.

The picture is set up for an NTSC TV (720x480, 60Hz). If the edges of the picture
are cut off, set OVERSCAN in retrotv-settings.txt, or use PICTURE SIZE in
the TV menu or SIZE on the phone remote. The page reloads
itself every morning at 5:45 to pick up updates.

AUDIO: the Pi sends full-level, evened-out sound, so keep the TV volume
low to medium. If you still hear a steady hum with nothing playing, it is
usually a ground loop between the Pi's power supply and the TV: plug both
into the same outlet strip, or add an inexpensive RCA ground loop isolator
on the audio cable. A TRRS cable with the wrong pin order can also hum; the
Pi needs the kind where the sleeve is video.

FAN: the card turns on a fan wired to GPIO 14 (physical pin 8) when the Pi
reaches 60 C, the same pin Raspberry Pi's own fan setting uses. The fan needs
its control wire on pin 8 and its power on a 5V pin (2 or 4). Physical pin 14
is a ground pin, so a fan wire there never gets power. A plain two-wire fan on
pins 4 and 6 simply runs all the time. To change the temperature, edit the
dtoverlay=gpio-fan line in config.txt (temp=60000 means 60 C).

TV STATUS: on the phone remote, open SET-UP and tap "tv status" for the Pi's
temperature, fan, Wi-Fi signal, power warnings, audio output and dropped
frames.

REAL REMOTE: a FLIRC USB receiver lets any old IR remote run the TV. Program
it once on a computer with the FLIRC app (choose the Full Keyboard controller),
pressing each remote button after clicking its key:
  0-9 = number keys        CH+/CH- = Up/Down arrows
  VOL+/VOL- = Right/Left   MUTE = M        POWER = P
  ENTER = Enter            MENU = Esc      GUIDE = G
  LAST/JUMP = Backspace    DISPLAY = I     SLEEP = S
  TV/VIDEO = V             PLAY = .  REW = ,  FF = /  EJECT = X
Then plug the FLIRC into the Pi. The full card is at
https://retrotv.conventionalmemory.io/ir-remote.html

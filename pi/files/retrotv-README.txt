RETRO TV FOR RASPBERRY PI

1. Open retrotv-wifi.txt on this card and fill in your Wi-Fi name and password.
   (Setting Wi-Fi in Raspberry Pi Imager's options when you write the card
   works too.)
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

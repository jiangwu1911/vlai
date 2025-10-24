#!/bin/bash

#ffmpeg -f x11grab -video_size 1920x1080 -r 30 -i :0.0 -f pulse -i alsa_input.usb-BlueTrm_UGREEN_CM564_USB_Audio_20220121000002-00.mono-fallback \
#	-c:v libx264 -c:a aac -ss 5 output.mp4

ffmpeg \
    -f x11grab -video_size 1920x1080 -framerate 30 -i :0.0 \
    -f pulse -i alsa_input.usb-BlueTrm_UGREEN_CM564_USB_Audio_20220121000002-00.mono-fallback \
    -c:v libx264 -b:v 5000k -maxrate 5000k -bufsize 10000k \
    -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    -ss 5 \
    output.mp4

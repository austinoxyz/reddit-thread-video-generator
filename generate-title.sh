#!/bin/sh
clear
rm -rf ./build-vid
mkdir -p ./build-vid/tmp
python3 automate-yt.py
vlc --quiet ./build-vid/title_card.mp4 > /dev/null 2>&1

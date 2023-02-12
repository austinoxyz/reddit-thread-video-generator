#!/usr/bin/bash
clear
rm -rf ./build-vid/
mkdir -p ./build-vid/tmp
python3 ./automate-yt.py
vlc --quiet ./build-vid/final.mp4 > /dev/null 2>&1

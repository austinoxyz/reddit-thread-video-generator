#!/usr/bin/bash
clear
rm -rf ./__pycache__
rm -rf ./build-vid/
mkdir -p ./build-vid/audio && mkdir ./build-vid/video
#cp ./res/static.mp4 ./build-vid
python3 src/automate-yt.py
vlc --no-one-instance --quiet ./final.mp4 > /dev/null 2>&1

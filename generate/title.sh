#!/bin/sh
clear
rm -rf ./__pycache__
rm -rf ./build-vid
mkdir -p ./build-vid/audio && mkdir ./build-vid/video
python3 automate-yt.py
vlc --quiet ./build-vid/video/title_card.mp4 > /dev/null 2>&1

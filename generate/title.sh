#!/bin/sh
clear
rm -rf ./__pycache__
rm -rf ./build-vid
mkdir -p ./build-vid/tmp
python3 automate-yt.py
vlc --quiet ./build-vid/title_card.mp4 > /dev/null 2>&1

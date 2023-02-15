#!/usr/bin/bash
clear
rm -rf ./__pycache__
rm -rf ./build-vid/
mkdir -p ./build-vid/tmp
cp ./res/static.mp4 ./build-vid
python3 ./automate-yt.py

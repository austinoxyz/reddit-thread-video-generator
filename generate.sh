#!/usr/bin/bash
clear
rm -rf ./tmp/ && rm -rf ./build-vid/
mkdir ./tmp/ && mkdir ./build-vid
python3 ./automate-yt.py
vlc --quiet ./build-vid/chain1.mp4

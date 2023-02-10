#!/bin/sh
clear
rm -rf ./build-vid
mkdir -p ./build-vid/tmp
python3 automate-yt.py
xdg-open ./build-vid/title_card.mp4

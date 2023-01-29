#!/usr/bin/bash
rm ~/Videos/automate-yt/*.*
python3 ./automate-yt.py
ln -s ~/Videos/automate-yt/final.mp4 .
xdg-open ./final.mp4

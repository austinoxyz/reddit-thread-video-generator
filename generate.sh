#!/usr/bin/bash
rm ~/Videos/automate-yt/*.*
python3 ./automate-yt.py
xdg-open ~/Videos/automate-yt/final.mp4

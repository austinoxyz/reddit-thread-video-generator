#!/usr/bin/bash
rm ~/Videos/automate-yt/tmp/*.mp3 ~/Videos/automate-yt/tmp/*.mp4 
rm ~/Videos/automate-yt/working/*.mp4 ~/Videos/automate-yt/working/*.txt
rm ~/Videos/automate-yt/final.mp4
python3 ./automate-yt.py
xdg-open ~/Videos/automate-yt/final.mp4

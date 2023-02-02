#!/usr/bin/bash
rm ~/Videos/automate-yt/tmp/*.mp3 ~/Videos/automate-yt/tmp/*.mp4 >> /dev/null
rm ~/Videos/automate-yt/working/*.mp4 ~/Videos/automate-yt/working/*.txt >> /dev/null
rm ~/Videos/automate-yt/final.mp4 >> /dev/null
python3 ~/Code/automate-yt/automate-yt.py
xdg-open ~/Videos/automate-yt/final.mp4 >> /dev/null

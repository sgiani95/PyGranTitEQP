#!/bin/bash
for f in *.png; do
    eog "$f" &
done
echo "Opened $(ls *.png | wc -l) PNGs in separate windows."

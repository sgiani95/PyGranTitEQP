#!/usr/bin/env bash

find . -type f -name gran_schwartz.png -print0 |
while IFS= read -r -d '' img; do
    echo "Opening $img"
    eog "$img"
done


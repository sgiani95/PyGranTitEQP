#!/usr/bin/env bash

find . -type f -name gran_functions.png -print0 |
while IFS= read -r -d '' img; do
    echo "Opening $img"
    eog "$img"
done


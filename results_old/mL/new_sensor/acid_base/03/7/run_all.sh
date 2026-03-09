#!/usr/bin/env bash
set -euo pipefail

PYTHON=/bin/python3
SCRIPT=/home/sgiani/repos/GranTED/main.py
BASE_OUT=./results

for ((i=5; i<=72; i++)); do
    echo "$i"
    head -$i data.dat > data_$i.dat

    outdir="${BASE_OUT}/${i}"
    mkdir -p "$outdir"
    outfile="data_$i.dat"

    "$PYTHON" "$SCRIPT" \
	--data_file "$outfile" \
        --output_dir "$outdir"

	mv $outfile $outdir
done


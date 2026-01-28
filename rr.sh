#!/usr/bin/env bash
set -euo pipefail

PYTHON=/bin/python3
SCRIPT=/home/sgiani/repos/GranTED/main.py
ODS=rawdata.ods
CSV=rawdata.csv
BASE_OUT=./results/strong_base

# Convert ODS to CSV
#soffice --headless \
#  --convert-to "csv:Text - txt - csv (StarCalc):44,34,UTF8" \
#  "$ODS"

# Count columns
ntriplets="12"

for ((i=1; i<=ntriplets; i++)); do

    "$PYTHON" "$SCRIPT" \
	--data_file "$outfile" \
        --output_dir "$outdir"

done


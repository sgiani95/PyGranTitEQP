#!/usr/bin/env bash
set -euo pipefail

PYTHON=/bin/python3
SCRIPT=/home/sgiani/repos/GranTED/main.py
ODS=rawdata.ods
CSV=rawdata.csv
BASE_OUT=/home/sgiani/repos/GranTED/results_old/mL/new_sensor/acid_base

# Convert ODS to CSV
soffice --headless \
  --convert-to "csv:Text - txt - csv (StarCalc):44,34,UTF8" \
  "$ODS"

# Count columns
ncols=$(awk -F',' 'NR==1 {print NF}' "$CSV")
ntriplets=$(( ncols / 3 ))

echo "Found $ntriplets triplets"

for ((i=1; i<=ntriplets; i++)); do
    col1=$(( (i-1)*3 + 1 ))
    col2=$(( col1 + 1 ))

    outdir="${BASE_OUT}/${i}"
    mkdir -p "$outdir"
    outfile="${outdir}/data.dat"

    echo "Processing triplet $i → columns $col1,$col2"

#    awk -F',' -v c1="$col1" -v c2="$col2" \
#        '{print $c1, $c2}' "$CSV" > "$outfile"
awk -F',' -v c1="$col1" -v c2="$col2" '{
    val1 = $c1
    val2 = ($c2 != "") ? $c2 : ""
    print val1, val2
}' "$CSV" > "$outfile"


    "$PYTHON" "$SCRIPT" \
	--data_file "$outfile" \
        --output_dir "$outdir"

done

echo ""; echo " read y"; read y

cd ${BASE_OUT}
rm -Rf 01 02 03 04
mkdir 01 ; mv 1 2 3 01
mkdir 02 ; mv 4 5 6 02
mkdir 03 ; mv 7 8 9 03
mkdir 04 ; mv 10 11 12 04

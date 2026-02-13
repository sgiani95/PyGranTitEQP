#!/usr/bin/env bash
set -euo pipefail

PYTHON=/bin/python3
SCRIPT=/home/sgiani/repos/GranTED/main.py
ODS=rawdata.ods
CSV=rawdata.csv
BASE_OUT=/home/sgiani/repos/GranTED/results/

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
    val2 = ($c2 != "") ? -$c2 : ""
    print val1, val2
}' "$CSV" > "$outfile"


    "$PYTHON" "$SCRIPT" \
	--data_file "$outfile" \
        --output_dir "$outdir"

done

echo ""; echo " read y"; read y

cd ${BASE_OUT}
rm -Rf 00_HCl_TRIS_01 00_HCl_TRIS_02 01_NaOH_KHP_02 M002_TiterNaOH_02 M003_TiterHCL_02 M011_TiterH2SO4_02 M400_2009 M140_Bro25 M120 M401_2006 M146_g084mwt_table M145mwt 70_Hcl_TRIS_Liquid_M003 80_Hcl_TRIS_Liquid_M003
mkdir 00_HCl_TRIS_01; mv 1 2 3 4 5 6 7 8 00_HCl_TRIS_01
mkdir 00_HCl_TRIS_02; mv 9 10 11 12 13 14 15 16 00_HCl_TRIS_02
mkdir 01_NaOH_KHP_02; mv 17 18 19 20 01_NaOH_KHP_02
mkdir M002_TiterNaOH_02; mv 21 22 23 24 25 26 M002_TiterNaOH_02
mkdir M003_TiterHCL_02; mv 27 28 29 30 31 32 M003_TiterHCL_02
mkdir M011_TiterH2SO4_02; mv 33 34 35 36 37 38 M011_TiterH2SO4_02
mkdir M400_2009; mv 39 M400_2009
mkdir M140_Bro25; mv 40 M140_Bro25
mkdir M120; mv 41 M120
mkdir M401_2006; mv 42 M401_2006
mkdir M146_g084mwt_table; mv 43 M146_g084mwt_table
mkdir M145mwt; mv 44 M145mwt
mkdir 70_Hcl_TRIS_Liquid_M003; mv 45 46 47 70_Hcl_TRIS_Liquid_M003
mkdir 80_Hcl_TRIS_Liquid_M003; mv 48 49 50 80_Hcl_TRIS_Liquid_M003


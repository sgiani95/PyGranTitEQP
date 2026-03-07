#!/usr/bin/env bash
# Collects the LAST line of report.csv from directories 1 to 72
# Appends them all into a single file in the current directory

set -euo pipefail  # exit on error, undefined variables, pipe errors

OUTPUT_FILE="all_last_lines_report.csv"
> "$OUTPUT_FILE"   # empty the file first (or remove this line if you want to append)

for dir in {1..111}; do
    csv_file="${dir}/report.csv"
    
    if [[ -f "$csv_file" ]]; then
        # Get the last line and append it with the directory number as prefix
        last_line=$(tail -n 1 "$csv_file")
        echo "${dir},${last_line}" >> "$OUTPUT_FILE"
        echo "Added last line from ${dir}/report.csv"
    else
        echo "Warning: ${csv_file} not found" >&2
    fi
done

echo "Done. All last lines collected in: $OUTPUT_FILE"
echo "Total lines collected: $(wc -l < "$OUTPUT_FILE")"

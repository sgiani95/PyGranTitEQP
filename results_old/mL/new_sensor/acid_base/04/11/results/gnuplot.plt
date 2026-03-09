# plot_eqp.gp - EQP vs directory with error bands + reference line

# set terminal pngcairo enhanced font "Arial,12" size 1200,800
# set output 'eqp_vs_directory_with_ref.png'

# Style
set style line 1 lc rgb '#0060ad' lt 1 lw 2.5 pt 7 ps 1.2
set style line 2 lc rgb '#0060ad' lt 1 lw 1.5
set style line 3 lc rgb '#ff0000' lt 2 lw 2.5

set title "Equivalence Point (Schwartz Optimized) vs Sample Directory" font ",16"
set xlabel "Directory / Sample ID" font ",14"
set ylabel "V_eq [mL]" font ",14"

set grid back lc rgb "#dddddd" lt 1 lw 1
set tics font ",12"
set key top left box opaque

set datafile separator ","     # ← important for CSV
set datafile missing "nan"     # treat missing as nan

file = "all_last_lines_report.csv"

plot file using 1:3:4 every ::1 with errorbars ls 1 title "EQP ± SE", \
     file using 1:3 every ::1 with linespoints title "EQP", \
     5.014 w lines ls 3 title "Reference = 5.014 mL"

pause -1

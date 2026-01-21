import os

# List of Python files in the order you want
py_files = [
    'main.py',
    'data_io.py',
    'preprocess.py',
    'gran_functions.py',
    'analyzer.py',
    'visualizer.py',
    'reporter.py'
]

# YAML header for Quarto PDF
qmd_content = """---
title: "Python Project GranTED"
author: "sgiani95"
format: 
  pdf:
    documentclass: article
    geometry: landscape
---

"""

# Add each Python file as a code chunk
for file in py_files:
    if os.path.exists(file):
        qmd_content += f"## {file}\n\n"
        qmd_content += f"```{{python}}\n#| echo: true\nprint(open('{file}').read())\n```\n\n"
    else:
        qmd_content += f"## {file} (not found)\n\n"

# Write the report.qmd
with open("report.qmd", "w") as f:
    f.write(qmd_content)

print("report.qmd created successfully!")

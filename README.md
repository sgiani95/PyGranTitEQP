# GranTED

**GranTED** (Gran--Schwartz Titration Equivalence point Determination) is an open-source Python tool for automated analysis of potentiometric titration data using the Gran and Schwartz methods.

Designed with analytical and green chemistry in mind, GranTED provides robust linear region detection, equivalence point calculation with uncertainty estimation, and advanced diagnostic plots, particularly useful for method development and validation.

---

## Features

- Automatic Gran and Schwartz function computation
- Robust linear interval detection with R² optimization
- k-optimization for Schwartz method
- Uncertainty estimation on equivalence point (EQP)
- Backward trimming analysis for method development (earliest acceptable volume detection)
- High-quality publication-ready plots (PNG + PDF)
- Multiple operation modes: `method_development`, `method_validation`, `method_application`, `method_debug`
- Command-line interface with extensive options

---

## Installation

```bash
git clone https://github.com/sgiani95/GranTED.git
cd GranTED
pip install -e .
```

---

## Quick Start

```bash
# Basic usage with default settings
granted --data_file data.dat --mode method_development

# With custom thresholds for method development
granted --data_file data.dat --mode method_development \
        --r2-min 0.99 \
        --unc-max 0.05 \
        --veq-tolerance 0.1 \
        --stability-window 3
```

---

![Logo](./logo.png)
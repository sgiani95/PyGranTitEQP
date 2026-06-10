"""
reporter.py: Exports analysis results to CSV and PDF formats.
Supports combined raw/opt tables for Gran/Schwartz; embeds PNGs in PDF; green chemistry stubs (optional).
"""

import pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import numpy as np
from typing import Dict, Any
from granted import main


def generate_pdf_report(results: Dict[str, Any], df: pd.DataFrame, params: Dict[str, Any], output_dir: Path) -> str:
    """
    Generate PDF report with title and metrics table.
    Table: Method, Vol EQP [mL], R2, Zones (difference)
    Rows: Gran Raw, Schwartz Opt
    Vol EQP to 3 decimals, R2 to 4 decimals.
    """
    Path(output_dir).mkdir(exist_ok=True)
    pdf_filename = output_dir / 'report.pdf'
    doc = SimpleDocTemplate(str(pdf_filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Step 1: Title
    title_style = styles['Heading2']
    titration_type = params.get('titration_type', 'acid_base')
    story.append(Paragraph(f"GranTED Report: {titration_type.title()}", title_style))
    story.append(Spacer(1, 12))

    # Step2: Gran/Schwartz graph (full width, preserved proportions)
    gran_path = output_dir / 'plots.png'
    if gran_path.exists():
        # Load image to get original dimensions
        from PIL import Image as PILImage
        with PILImage.open(gran_path) as img:
            orig_width, orig_height = img.size
        # Calculate height to preserve ratio at desired width
        target_width = 340  # Fits letter page margins
        target_height = int(target_width * orig_height / orig_width)
        img = Image(str(gran_path), width=target_width, height=target_height)
        story.append(img)
        story.append(Spacer(1, 12))
    else:
        story.append(Paragraph("Gran/Schwartz graph not found", styles['Normal']))
        story.append(Spacer(1, 12))

    # Step 3: Metrics table
    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    # Calculate difference for zones
    raw_zone_diff = gran_raw.get('zone_end', 0) - gran_raw.get('zone_start', 0)
    opt_zone_diff = sch_opt.get('zone_end', 0) - sch_opt.get('zone_start', 0)

    table_data = [
        ['Method', 'Vol EQP [mL]', 'R2', 'Zones (difference)'],
        [
            'Gran Raw',
            f"{gran_raw.get('V_eq', 'N/A'):.3f}",
            f"{gran_raw.get('r2', 'N/A'):.4f}",
            f"{gran_raw.get('zone_start', 'N/A'):02d}-{gran_raw.get('zone_end', 'N/A'):02d} ({raw_zone_diff:02d})"
        ],
        [
            'Schwartz Opt',
            f"{sch_opt.get('V_eq', 'N/A'):.3f}",
            f"{sch_opt.get('r2', 'N/A'):.4f}",
            f"{sch_opt.get('zone_start', 'N/A'):02d}-{sch_opt.get('zone_end', 'N/A'):02d} ({opt_zone_diff:02d})"
        ],
    ]

    table = Table(table_data)
    table.setStyle(TableStyle([
        # Header: bold, same size
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),

    # Body: normal, same size
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 10),

    # Uniform padding
    ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ('TOPPADDING', (0, 0), (-1, -1), 1),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),

    # Alignment: First column LEFT, rest CENTER
    ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Column 0 (Parameter) right-aligned
    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),   # Columns 1 to end centered
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
]))
    
    story.append(table)
    # story.append(Spacer(1, 12))

    # Footer: random 10Print pattern + timestamp
    footer_text = ""

    # Generate random 10Print pattern (4 rows, 50 chars wide)
    import random
    for row in range(4):  # Number of rows — adjust as you like
        row_text = ""
        for _ in range(7):  # Width — adjust as you like
            if random.randrange(0, 10) >= 5:
                row_text += " / "
            else:
                row_text += " \\ "
        footer_text += row_text.rstrip() + "\n"  # Remove trailing spaces

    # Add timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    footer_text += f"\n / / \ GranTED version {__version__} | Generated on: {timestamp}"

    # Add as preformatted text (monospace, small font)
# Footer style: Helvetica, small size, left-aligned
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        alignment=0,  # Left
        leading=20,   # Line spacing
    )
    
    story.append(Spacer(1, 15))  # Space above footer
    story.append(Paragraph("<pre>" + footer_text + "</pre>", footer_style))

    doc.build(story)
    return str(pdf_filename)


def generate_csv_report_development(
    df: pd.DataFrame,
    params: Dict[str, Any],
    results: Dict[str, Any],
    collected: Dict[str, list],
    earliest_n: int | None,
    reference_veq: float | None,
    output_dir: Path
) -> str:
    """
    Special 4-line report for method_development mode.
    """
    Path(output_dir).mkdir(exist_ok=True)
    csv_filename = output_dir / 'report.csv'

    # Full dataset results
    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    # Vopt result
    vopt_data = {'V_eq': np.nan, 'V_eq_unc': np.nan, 'r2': np.nan, 
                 'zone_start': 'N/A', 'zone_end': 'N/A', 'max_volume': np.nan}

    if earliest_n is not None and earliest_n in collected.get('n_points', []):
        idx = collected['n_points'].index(earliest_n)
        vopt_data = {
            'V_eq': collected['V_eq'][idx],
            'V_eq_unc': collected['V_eq_unc'][idx],
            'r2': collected['R2'][idx],
            'zone_start': collected.get('zone_start', [None])[idx] or 'N/A',
            'zone_end': collected.get('zone_end', [None])[idx] or 'N/A',
            'max_volume': collected['max_volume'][idx]
        }

    def safe_float(value, decimals=3):
        if isinstance(value, (int, float)) and not np.isnan(value):
            return f"{value:.{decimals}f}"
        return "nan"

    csv_data = [
        ['Method', 'V_eq [mL]', 'V_eq_unc [mL]', 'R²', 'Zones (start-end)', 'Max Volume Used [mL]', 'Notes'],
        [
            'Gran Raw (full data)',
            safe_float(gran_raw.get('V_eq')),
            safe_float(gran_raw.get('V_eq_unc')),
            safe_float(gran_raw.get('r2'), 4),
            f"{gran_raw.get('zone_start', 'N/A')}-{gran_raw.get('zone_end', 'N/A')}",
            safe_float(params.get('volume_array', [0])[-1]),
            'EQP* on full dataset'
        ],
        [
            'Schwartz Optimized (full data)',
            safe_float(sch_opt.get('V_eq')),
            safe_float(sch_opt.get('V_eq_unc')),
            safe_float(sch_opt.get('r2'), 4),
            f"{sch_opt.get('zone_start', 'N/A')}-{sch_opt.get('zone_end', 'N/A')}",
            safe_float(params.get('volume_array', [0])[-1]),
            'EQP* on full dataset'
        ],
        [
            'Vopt Result',
            safe_float(vopt_data.get('V_eq')),
            safe_float(vopt_data.get('V_eq_unc')),
            safe_float(vopt_data.get('r2'), 4),
            f"{vopt_data.get('zone_start', 'N/A')}-{vopt_data.get('zone_end', 'N/A')}",
            safe_float(vopt_data.get('max_volume')),
            f'Earliest acceptable point (n={earliest_n})'
        ]
    ]

    import csv
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)

    print(f"Development report saved: {csv_filename}")
    return str(csv_filename)


def generate_csv_report_validation(
    df: pd.DataFrame,
    params: Dict[str, Any],
    results_full: Dict[str, Any],
    results_vopt: Dict[str, Any],
    vopt_volume: float,
    output_dir: Path
) -> str:
    """
    Dedicated report for method_validation mode.
    """
    Path(output_dir).mkdir(exist_ok=True)
    csv_filename = output_dir / 'validation_report.csv'

    # Full dataset results
    gran_full = results_full.get('gran', {}).get('raw', {})
    sch_full = results_full.get('schwartz', {}).get('opt', {})

    # Vopt (trimmed) results
    gran_vopt = results_vopt.get('gran', {}).get('raw', {})
    sch_vopt = results_vopt.get('schwartz', {}).get('opt', {})

    def safe_float(value, decimals=3):
        if isinstance(value, (int, float)) and not np.isnan(value):
            return f"{value:.{decimals}f}"
        return "nan"

    csv_data = [
        ['Method', 'V_eq [mL]', 'V_eq_unc [mL]', 'R²', 'Zones (start-end)', 'Notes'],
        [
            'Gran Raw (full validation)',
            safe_float(gran_full.get('V_eq')),
            safe_float(gran_full.get('V_eq_unc')),
            safe_float(gran_full.get('r2'), 4),
            f"{gran_full.get('zone_start', 'N/A')}-{gran_full.get('zone_end', 'N/A')}",
            'EQP* on full validation dataset'
        ],
        [
            'Schwartz Optimized (full validation)',
            safe_float(sch_full.get('V_eq')),
            safe_float(sch_full.get('V_eq_unc')),
            safe_float(sch_full.get('r2'), 4),
            f"{sch_full.get('zone_start', 'N/A')}-{sch_full.get('zone_end', 'N/A')}",
            'EQP* on full validation dataset'
        ],
        [
            'Vopt Result (validation)',
            safe_float(sch_vopt.get('V_eq')),
            safe_float(sch_vopt.get('V_eq_unc')),
            safe_float(sch_vopt.get('r2'), 4),
            f"{sch_vopt.get('zone_start', 'N/A')}-{sch_vopt.get('zone_end', 'N/A')}",
            f'Trimmed to V_opt = {vopt_volume:.3f} mL'
        ]
    ]

    import csv
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)

    print(f"Validation report saved: {csv_filename}")
    return str(csv_filename)


def generate_csv_report_application(
    df: pd.DataFrame,
    params: Dict[str, Any],
    results: Dict[str, Any],
    output_dir: Path
) -> str:
    """
    Simple report for method_application mode.
    Data is already trimmed to V_opt.
    """
    Path(output_dir).mkdir(exist_ok=True)
    csv_filename = output_dir / 'application_report.csv'

    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    def safe_float(value, decimals=3):
        if isinstance(value, (int, float)) and not np.isnan(value):
            return f"{value:.{decimals}f}"
        return "nan"

    csv_data = [
        ['Method', 'V_eq [mL]', 'V_eq_unc [mL]', 'R²', 'Zones (start-end)', 'Notes'],
        [
            'Gran Raw',
            safe_float(gran_raw.get('V_eq')),
            safe_float(gran_raw.get('V_eq_unc')),
            safe_float(gran_raw.get('r2'), 4),
            f"{gran_raw.get('zone_start', 'N/A')}-{gran_raw.get('zone_end', 'N/A')}",
            'EQP on data trimmed to V_opt'
        ],
        [
            'Schwartz Optimized',
            safe_float(sch_opt.get('V_eq')),
            safe_float(sch_opt.get('V_eq_unc')),
            safe_float(sch_opt.get('r2'), 4),
            f"{sch_opt.get('zone_start', 'N/A')}-{sch_opt.get('zone_end', 'N/A')}",
            'EQP on data trimmed to V_opt'
        ]
    ]

    import csv
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)

    print(f"Application report saved: {csv_filename}")
    return str(csv_filename)


def generate_csv_report4(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: Path) -> str:
    """
    Generate simple CSV report with the requested format:
    Method,V_eq [mL],R²,Zones (start-end)
    Gran Raw,4.096,0.9995,15-30
    Schwartz Optimized,4.086,0.9999,12-27
    """
    Path(output_dir).mkdir(exist_ok=True)
    csv_filename = output_dir / 'report.csv'

    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    # Format zones as start-end
    raw_zone = f"{gran_raw.get('zone_start', 'N/A')}-{gran_raw.get('zone_end', 'N/A')}"
    opt_zone = f"{sch_opt.get('zone_start', 'N/A')}-{sch_opt.get('zone_end', 'N/A')}"

    # Safe formatting function
    def safe_float(value, decimals):
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        return str(value)  # 'N/A' or other string

    csv_data = [
    ['Method', 'V_eq [mL]', 'V_eq_unc [mL]', 'R²', 'Zones (start-end)'],
    [
        'Gran Raw',
        safe_float(gran_raw.get('V_eq'), 3),
        safe_float(gran_raw.get('V_eq_unc'), 3),
        safe_float(gran_raw.get('r2'), 4),
        raw_zone
    ],
    [
        'Schwartz Optimized',
        safe_float(sch_opt.get('V_eq'), 3),
        safe_float(sch_opt.get('V_eq_unc'), 3),
        safe_float(sch_opt.get('r2'), 4),
        opt_zone
    ]
]

    import csv
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(csv_data)

    return str(csv_filename)


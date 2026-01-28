"""
reporter.py: Generates multi-format reports (CSV, PDF) for GranTED titration analysis.

Exports raw data + metrics to a single CSV; PDF with dynamic tables and optional embedded plot buffers.
Timestamps in PDF text only (title/date); no timestamps in filenames.
Graceful fallbacks for partial results. Green chemistry placeholders included.

Dependencies: pandas, pathlib, reportlab (for PDF), logging.
"""

import logging
import pandas as pd
import numpy as np  # For np.isnan in serialization
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from io import BytesIO  # For buffer handling in PDF embeds

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image  # For embedding buffers/PNGs


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def convert_to_serializable(obj: Any) -> Any:
    """
    Recursively convert non-JSON serializable objects (e.g., NumPy) to lists/str.
    """
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    elif isinstance(obj, (dict, list)):
        return {k: convert_to_serializable(v) for k, v in obj.items()} if isinstance(obj, dict) else [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None  # Handle NaN
    return str(obj)  # Fallback


def export_to_csv(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], output_dir: Path) -> str:
    """
    Export to a single CSV: Raw data followed by metrics (combined Gran/Schwartz raw/opt table).
    Handles missing keys gracefully with 'N/A'.
    """
    try:
        csv_filename = output_dir / "report.csv"
        # Section 1: Raw data (original style)
        with open(csv_filename, 'w') as f:
            f.write("=== RAW DATA ===\n")
            df.to_csv(f, index=False, mode='a')
            f.write("\n\n=== METRICS ===\n")
        
        # Section 2: Metrics (DataFrame for combined table)
        data = []
        methods = ['gran', 'schwartz'] if 'schwartz' in results else ['gran']
        for method in methods:
            raw = results[method].get('raw', {})
            opt = results[method].get('opt', {})
            data.append({
                'Method': f'{method.capitalize()} Raw',
                'V_eq (mL)': raw.get('V_eq', 'N/A'),
                'R²': raw.get('r2', 'N/A'),
                'k5': raw.get('k5', 'N/A'),
                'Zones (start-end)': f"{raw.get('zone_start', 'N/A')}-{raw.get('zone_end', 'N/A')}"
            })
            data.append({
                'Method': f'{method.capitalize()} Optimized',
                'V_eq (mL)': opt.get('V_eq', 'N/A'),
                'R²': opt.get('r2', 'N/A'),
                'k5': opt.get('k5', 'N/A'),
                'Zones (start-end)': f"{opt.get('zone_start', 'N/A')}-{opt.get('zone_end', 'N/A')}"
            })
        
        if not data:
            data = [{'Method': 'No Data', 'V_eq (mL)': 'N/A', 'R²': 'N/A', 'k5': 'N/A', 'Zones (start-end)': 'N/A', 'Green Savings (L)': 0.0}]
        
        metrics_df = pd.DataFrame(data)
        with open(csv_filename, 'a') as f:
            metrics_df.to_csv(f, index=False, mode='a')
        
        print(f"Saved CSV report to {csv_filename}")
        return str(csv_filename)
    except Exception as e:
        print(f"CSV export failed: {e}")
        return ""

def generate_pdf_report(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any], 
                        output_dir: Path, embed_in_pdf: bool = False) -> str:
    """
    Generate PDF report with metrics table and embedded PNGs.
    Optional embed_in_pdf flag (unused for now, but future-proof).
    """
    Path(output_dir).mkdir(exist_ok=True)
    pdf_filename = output_dir / 'report.pdf'
    # doc = SimpleDocTemplate(str(pdf_filename), pagesize=letter)
    # Set page size to landscape
    doc = SimpleDocTemplate(str(pdf_filename), pagesize=landscape(letter))
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=30)
    titration_type = params.get('titration_type', 'weak_acid')
    story.append(Paragraph(f"GranTED Report: {titration_type.title()} Titration", title_style))
    story.append(Spacer(1, 12))

    # Combined metrics table (4 rows: Gran/Schwartz raw/opt)
    data = [['Method', 'V_eq (mL)', 'R²', 'k5', 'Zones (start-end)']]
    methods = ['gran', 'schwartz']
    for method in methods:
        if method in results:
            raw = results[method].get('raw', {})
            opt = results[method].get('opt', {})
            data.append([
                f'{method.capitalize()} Raw',
                raw.get('V_eq', 'N/A'),
                raw.get('r2', 'N/A'),
                raw.get('k5', 'N/A'),
                f"{raw.get('zone_start', 'N/A')}-{raw.get('zone_end', 'N/A')}"
            ])
            data.append([
                f'{method.capitalize()} Optimized',
                opt.get('V_eq', 'N/A'),
                opt.get('r2', 'N/A'),
                opt.get('k5', 'N/A'),
                f"{opt.get('zone_start', 'N/A')}-{opt.get('zone_end', 'N/A')}"
            ])

    if len(data) == 1:
        data.append(['No Data', 'N/A', 'N/A', 'N/A', 'N/A'])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 12))

    # Embed PNGs (safe loading, proportional)
    png_files = ['titration_curve.png', 'gran_schwartz.png']
    existing_pngs = [output_dir / png for png in png_files if (output_dir / png).exists()]

    if existing_pngs:
        # Calculate width for each image (50% of page width minus a small gap)
        gap = 12  # points
        img_width = (doc.width - gap) / 2

        img_row = []
        for png_path in existing_pngs:
            img = Image(str(png_path))
            aspect = img.imageHeight / img.imageWidth
            img.drawWidth = img_width
            img.drawHeight = img_width * aspect
            img_row.append(img)

        # Add images side by side using a Table
        table = Table([img_row], colWidths=[img.drawWidth for img in img_row])
        table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(table)
        story.append(Spacer(1, 12))
    else:
        for png in png_files:
            story.append(Paragraph(f"Placeholder: {png} not found - run visualizer first.", styles['Normal']))
            story.append(Spacer(1, 12))

    doc.build(story)
    print(f"Saved PDF report with embeds to {pdf_filename}")
    return str(pdf_filename)

def generate_report(df: pd.DataFrame, params: Dict[str, Any], results: Dict[str, Any],
                    output_dir: str = '.', include_plots: bool = False,
                    buffers: Optional[Dict[str, BytesIO]] = None) -> Dict[str, str]:
    """
    Orchestrate full report generation: CSV, PDF (no JSON).
    Handles missing results gracefully; no timestamps in filenames.
    """
    if not results:
        logger.warning("No results provided—generating skeleton report (params only).")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    outputs = {}
    
    # Single CSV
    csv_file = export_to_csv(df, params, results, output_dir)
    outputs['csv'] = [csv_file] if csv_file else []
    
    # PDF
    pdf_file = generate_pdf_report(df=df, params=params, results=results, output_dir=output_dir, embed_in_pdf=include_plots)
    outputs['pdf'] = [pdf_file] if pdf_file else []
    
    logger.info(f"Full report generated in {output_dir} ({sum(len(v) for v in outputs.values())} files).")
    return outputs


if __name__ == "__main__":
    # Standalone test: Mock inputs
    df = pd.DataFrame({'volume': [0, 1, 2], 'potential': [0, -100, -200]})
    params = {'titration_type': 'weak_acid', 'V': 25.0, 'C_B': 0.1}
    results = {
        'gran': {
            'raw': {'r2': 0.95, 'v_eq': 10.2, 'zone_start': 5, 'zone_end': 15},
            'optimized': {'r2': 0.98, 'v_eq': 10.5, 'zone_start': 6, 'zone_end': 14}
        }
    }
    # Mock buffers (in real: from visualize_all(..., embed_in_pdf=True))
    mock_buffers = {}  # Or populate with BytesIO for test
    outputs = generate_report(df, params, results, output_dir='./output', include_plots=True, buffers=mock_buffers)
    print("Test outputs:", outputs)
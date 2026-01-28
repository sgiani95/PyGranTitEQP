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

def generate_pdf_report(results: Dict[str, Any], df: pd.DataFrame, params: Dict[str, Any], 
                        output_dir: Path, embed_in_pdf: bool = False) -> str:
    """
    Generate PDF report with metrics table and embedded images.
    Accepts embed_in_pdf flag (for future buffer usage if needed).
    """
    Path(output_dir).mkdir(exist_ok=True)
    pdf_filename = output_dir / 'report.pdf'
    doc = SimpleDocTemplate(str(pdf_filename), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = styles['Heading1']
    titration_type = params.get('titration_type', 'acid_base')
    story.append(Paragraph(f"GranTED Report: {titration_type.title()}", title_style))
    story.append(Spacer(1, 12))

    # Metrics table (Gran Raw vs Schwartz Optimized)
    gran_raw = results.get('gran', {}).get('raw', {})
    sch_opt = results.get('schwartz', {}).get('opt', {})

    data = [
        ['Parameter', 'Gran Raw', 'Schwartz Optimized', 'Difference'],
        ['R²', f"{gran_raw.get('r2', 'N/A'):.4f}", f"{sch_opt.get('r2', 'N/A'):.4f}", 
         f"{(sch_opt.get('r2', 0.0) - gran_raw.get('r2', 0.0)):.4f}" if isinstance(gran_raw.get('r2', 0.0), float) and isinstance(sch_opt.get('r2', 0.0), float) else 'N/A'],
        ['V_eq (mL)', f"{gran_raw.get('V_eq', 'N/A'):.3f}", f"{sch_opt.get('V_eq', 'N/A'):.3f}", 
         f"{(sch_opt.get('V_eq', 0.0) - gran_raw.get('V_eq', 0.0)):.3f}" if isinstance(gran_raw.get('V_eq', 0.0), float) and isinstance(sch_opt.get('V_eq', 0.0), float) else 'N/A'],
        ['Zone Start (mL)', gran_raw.get('zone_start', 'N/A'), sch_opt.get('zone_start', 'N/A'), 'N/A'],
        ['Zone End (mL)', gran_raw.get('zone_end', 'N/A'), sch_opt.get('zone_end', 'N/A'), 'N/A'],
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)
    story.append(Spacer(1, 24))

    # Titration curve
    curve_path = output_dir / 'titration_curve.png'
    if curve_path.exists():
        img = Image(str(curve_path), width=500, height=300)
        story.append(img)
        story.append(Spacer(1, 12))

    # Gran/Schwartz graph
    gran_path = output_dir / 'gran_schwartz.png'
    if gran_path.exists():
        img = Image(str(gran_path), width=500, height=600)
        story.append(img)
        story.append(Spacer(1, 12))

    doc.build(story)
    print(f"Saved PDF report to {pdf_filename}")
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
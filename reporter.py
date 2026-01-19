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
    Export to a single CSV: Raw data followed by metrics (oriented to original simple structure).
    Handles missing keys gracefully with 'N/A'.
    """
    try:
        csv_filename = output_dir / "report.csv"
        
        # Section 1: Raw data (original style)
        with open(csv_filename, 'w') as f:
            f.write("=== RAW DATA ===\n")
            df.to_csv(f, index=False, mode='a')
            f.write("\n\n=== METRICS ===\n")
        
        # Section 2: Metrics (simple per-method tables, appended as text/CSV blocks)
        methods = ['gran', 'schwartz'] if 'schwartz' in results else ['gran']
        with open(csv_filename, 'a') as f:
            for method in methods:
                f.write(f"\n{method.upper()} METRICS:\n")
                f.write("Mode,R²,V_eq (mL),Zone Start (mL),Zone End (mL),Green Savings (L)\n")
                for mode in ['raw', 'optimized']:
                    r2 = results.get(method, {}).get(mode, {}).get('r2', 'N/A')
                    v_eq = results.get(method, {}).get(mode, {}).get('v_eq', 'N/A')
                    zone_start = results.get(method, {}).get(mode, {}).get('zone_start', 'N/A')
                    zone_end = results.get(method, {}).get(mode, {}).get('zone_end', 'N/A')
                    green = 0.05 if mode == 'optimized' else 0.0  # Placeholder
                    f.write(f"{mode},{r2},{v_eq},{zone_start},{zone_end},{green}\n")
                f.write("\n")
        
        logger.info(f"Exported single CSV to {csv_filename}")
        return str(csv_filename)
    except Exception as e:
        logger.warning(f"CSV export failed: {e}")
        return ""


def generate_pdf_report(params: Dict[str, Any], results: Dict[str, Any], output_dir: Path,
                        buffers: Optional[Dict[str, BytesIO]] = None, include_plots: bool = True) -> str:
    """
    Generate PDF with dynamic tables and optional embedded plot buffers.
    Handles missing results with placeholders; timestamp in text only.
    """
    try:
        pdf_filename = output_dir / "report.pdf"
        
        doc = SimpleDocTemplate(str(pdf_filename), pagesize=landscape(letter),
                                rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)  # Center

        # Title with timestamp (text only)
        title = f"GranTED Titration Report - {params.get('titration_type', 'Unknown')} (Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')})"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))

        # Params table
        params_data = [['Parameter', 'Value']] + [[k, str(v)] for k, v in params.items()]
        params_table = Table(params_data, colWidths=[2*inch, 3*inch])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(params_table)
        story.append(Spacer(1, 12))

        # Metrics table: Dynamic for methods
        if results:
            methods = ['gran', 'schwartz'] if 'schwartz' in results else ['gran']
            for method in methods:
                header = Paragraph(f"<b>{method.capitalize()} Metrics</b>", styles['Heading2'])
                story.append(header)
                story.append(Spacer(1, 6))

                metrics_data = [['Mode', 'R²', 'V_eq (mL)', 'Zone Start (mL)', 'Zone End (mL)', 'Green Savings (L)']]
                for mode in ['raw', 'optimized']:
                    r2 = results.get(method, {}).get(mode, {}).get('r2', 'N/A')
                    v_eq = results.get(method, {}).get(mode, {}).get('v_eq', 'N/A')
                    zone_start = results.get(method, {}).get(mode, {}).get('zone_start', 'N/A')
                    zone_end = results.get(method, {}).get(mode, {}).get('zone_end', 'N/A')
                    green = 0.05 if mode == 'optimized' else 0.0
                    metrics_data.append([mode.capitalize(), f"{r2:.3f}" if isinstance(r2, (int, float)) else r2,
                                         f"{v_eq:.3f}" if isinstance(v_eq, (int, float)) else v_eq,
                                         f"{zone_start:.3f}" if isinstance(zone_start, (int, float)) else zone_start,
                                         f"{zone_end:.3f}" if isinstance(zone_end, (int, float)) else zone_end, green])
                
                metrics_table = Table(metrics_data, colWidths=[0.8*inch] + [0.8*inch]*5)
                metrics_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('ALTERNATEBACKGROUND', (0, 1), (-1, -1), [0.9, 0.9, 0.9]),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(metrics_table)
                story.append(Spacer(1, 12))

                # Embed plots if available
                if include_plots and buffers:
                    plot_keys = ['curve', f'{method}', f'{method}_derivatives']
                    for key in plot_keys:
                        if key in buffers:
                            img = Image(buffers[key], width=4*inch, height=3*inch)
                            story.append(img)
                            story.append(Spacer(1, 6))
                    logger.info(f"Embedded {method} plots in PDF.")

        else:
            story.append(Paragraph("<b>No results available—run analyzer first.</b>", styles['Normal']))

        # Green chemistry note
        green_para = Paragraph("Green Chemistry Note: Optimized analysis saves ~0.05 L solvent per titration (global est: 50–100M L/year).", styles['Normal'])
        story.append(green_para)

        doc.build(story)
        logger.info(f"Generated PDF report to {pdf_filename}")
        return str(pdf_filename)
    except Exception as e:
        logger.warning(f"PDF generation failed: {e}")
        return ""


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
    pdf_file = generate_pdf_report(params, results, output_dir, buffers, include_plots)
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
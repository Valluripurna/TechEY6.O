import os
import io
from fpdf import FPDF
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import requests
from typing import List, Dict, Any, Callable, Optional
import collections
import os

# Import image search functionality
from data_sources import gemini_websearch

# Resolve a stable output directory under the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

class StyledPDF(FPDF):
    def header(self):
        self.set_fill_color(240, 248, 255)
        self.set_text_color(33, 37, 41)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 12, 'Pharma Mind Nexus Report', 0, 1, 'C', fill=True)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def _pdf_add_section(pdf: FPDF, title: str):
    pdf.set_font('Arial', 'B', 12)
    pdf.set_fill_color(230, 230, 250)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, title, 0, 1, 'L', fill=True)
    pdf.ln(2)

def _pdf_add_table(pdf: FPDF, rows: list[dict]):
    if not rows:
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 8, 'No data available.')
        pdf.ln(2)
        return
    # headers
    headers = list(rows[0].keys())
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_text_color(52, 58, 64)
    col_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width /= max(1, len(headers))
    for h in headers:
        pdf.cell(col_width, 8, str(h)[:30], 1, 0, 'L', fill=True)
    pdf.ln(8)
    # rows
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(33, 37, 41)
    for r in rows:
        for h in headers:
            val = r.get(h, '')
            pdf.cell(col_width, 8, str(val)[:30], 1, 0, 'L')
        pdf.ln(8)
    pdf.ln(4)

def _pdf_add_text(pdf: FPDF, content):
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(33, 37, 41)
    if isinstance(content, (dict, list)):
        # Convert JSON to readable text with key: value lines
        if isinstance(content, dict):
            for k, v in content.items():
                if isinstance(v, (dict, list)):
                    pdf.multi_cell(0, 6, f"{k}:")
                    _pdf_add_text(pdf, v)
                else:
                    pdf.multi_cell(0, 6, f"{k}: {v}")
        else:
            for item in content:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, (dict, list)):
                            pdf.multi_cell(0, 6, f"{k}:")
                            _pdf_add_text(pdf, v)
                        else:
                            pdf.multi_cell(0, 6, f"{k}: {v}")
                    pdf.ln(1)
                else:
                    pdf.multi_cell(0, 6, str(item))
    else:
        pdf.multi_cell(0, 6, str(content))
    pdf.ln(2)

def _pdf_add_image(pdf: FPDF, url: str, width: int = 120):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            # Save to a buffer
            buf = io.BytesIO(resp.content)
            tmp_path = os.path.join(OUTPUT_DIR, f"img_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png")
            with open(tmp_path, 'wb') as f:
                f.write(buf.getbuffer())
            pdf.image(tmp_path, w=width)
            pdf.ln(4)
            try:
                os.remove(tmp_path)
            except:
                pass
    except Exception:
        # Ignore image errors
        pass

def _pdf_add_chart(pdf: FPDF, title: str, labels: list, values: list):
    try:
        plt.figure(figsize=(5,3))
        plt.bar(labels, values, color=['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc949'])
        plt.title(title)
        plt.xticks(rotation=45, ha='right', fontsize=8)
        plt.tight_layout()
        chart_path = os.path.join(OUTPUT_DIR, f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png")
        plt.savefig(chart_path, dpi=200)
        plt.close()
        pdf.image(chart_path, w=170)
        pdf.ln(4)
        try:
            os.remove(chart_path)
        except Exception:
            pass
    except Exception:
        # If chart fails, skip silently
        pass

def _pdf_add_pie_chart(pdf: FPDF, title: str, labels: list, values: list):
    try:
        plt.figure(figsize=(5,3))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title(title)
        plt.tight_layout()
        chart_path = os.path.join(OUTPUT_DIR, f"pie_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png")
        plt.savefig(chart_path, dpi=200)
        plt.close()
        pdf.image(chart_path, w=170)
        pdf.ln(4)
        try:
            os.remove(chart_path)
        except Exception:
            pass
    except Exception:
        pass

# Dynamic chart rules: section -> function that returns (labels, values, title) or None
ChartRule = Callable[[str, Any], Optional[tuple[list, list, str]]]

def exim_chart_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:
    if section.lower().startswith('exim') and isinstance(content, list) and content:
        # common keys: country, value or amount/total
        labels_key = next((k for k in ['country', 'partner', 'destination'] if all(isinstance(i.get(k), str) for i in content if isinstance(i, dict))), None)
        value_key = next((k for k in ['value', 'amount', 'total', 'trade_value'] if all(isinstance(i.get(k), (int, float)) for i in content if isinstance(i, dict))), None)
        if labels_key and value_key:
            labels = [str(i.get(labels_key)) for i in content if isinstance(i, dict)][:10]
            values = [float(i.get(value_key)) for i in content if isinstance(i, dict)][:10]
            return labels, values, f"{section} - {value_key}"
    return None

def generic_numeric_chart_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:

    def trials_phase_pie_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:
        if 'trial' in section.lower() and isinstance(content, list) and content:
            phases = [ (i.get('phase') or i.get('trial_phase') or '').strip() for i in content if isinstance(i, dict) ]
            phases = [p for p in phases if p]
            if phases:
                counter = collections.Counter(phases)
                labels = list(counter.keys())[:8]
                values = [counter[l] for l in labels]
                return labels, values, f"{section} - Phase Distribution"
        return None

    def patents_assignee_pie_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:
        if 'patent' in section.lower() and isinstance(content, list) and content:
            assignees = [ (i.get('assignee') or i.get('assignees') or '').strip() for i in content if isinstance(i, dict) ]
            assignees = [a for a in assignees if a]
            if assignees:
                counter = collections.Counter(assignees)
                labels = list(counter.keys())[:8]
                values = [counter[l] for l in labels]
                return labels, values, f"{section} - Assignee Share"
        return None
    if isinstance(content, list) and content and isinstance(content[0], dict):
        keys = list(content[0].keys())
        num_key = next((k for k in keys if all(isinstance(i.get(k), (int, float)) for i in content if isinstance(i, dict))), None)
        label_key = next((k for k in keys if all(isinstance(i.get(k), str) for i in content if isinstance(i, dict))), None)
        if num_key and label_key:
            labels = [str(i.get(label_key)) for i in content if isinstance(i, dict)][:10]
            values = [float(i.get(num_key)) for i in content if isinstance(i, dict)][:10]
            return labels, values, f"{section} - {num_key}"
    return None

# --- Pie Chart Rules (ensure defined before CHART_RULES) ---
def trials_phase_pie_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:
    if 'trial' in section.lower() and isinstance(content, list) and content:
        phases = [ (i.get('phase') or i.get('trial_phase') or '').strip() for i in content if isinstance(i, dict) ]
        phases = [p for p in phases if p]
        if phases:
            counter = collections.Counter(phases)
            labels = list(counter.keys())[:8]
            values = [counter[l] for l in labels]
            return labels, values, f"{section} - Phase Distribution"
    return None

def patents_assignee_pie_rule(section: str, content: Any) -> Optional[tuple[list, list, str]]:
    if 'patent' in section.lower() and isinstance(content, list) and content:
        assignees = [ (i.get('assignee') or i.get('assignees') or '').strip() for i in content if isinstance(i, dict) ]
        assignees = [a for a in assignees if a]
        if assignees:
            counter = collections.Counter(assignees)
            labels = list(counter.keys())[:8]
            values = [counter[l] for l in labels]
            return labels, values, f"{section} - Assignee Share"
    return None

CHART_RULES: List[ChartRule] = [
    exim_chart_rule,
    trials_phase_pie_rule,
    patents_assignee_pie_rule,
    generic_numeric_chart_rule,
]

def generate_pdf_report(query, data, filename=None):
    """Generate a PDF report from the given data."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.pdf"
    # Build absolute path in OUTPUT_DIR
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    pdf = StyledPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(0, 102, 204)
    # Title block
    title_line = f"Pharma Research Report: {str(query or '').strip() or 'Pharmaceutical Research'}"
    pdf.multi_cell(0, 8, title_line)
    ts = datetime.now().strftime("Generated on: %B %d, %Y at %H:%M")
    pdf.set_text_color(108, 117, 125)
    pdf.multi_cell(0, 6, ts)
    pdf.set_text_color(33, 37, 41)
    pdf.ln(2)

    # Executive Summary
    _pdf_add_section(pdf, "Executive Summary")
    summary_para = (
        f"This comprehensive analysis of {str(query or 'Pharmaceutical Research')} covers market dynamics, "
        f"intellectual property, clinical development, and web intelligence. The findings suggest ongoing "
        f"innovation and commercial interest in this therapeutic area."
    )
    _pdf_add_text(pdf, summary_para)
    
    # Add an image related to the query if available
    try:
        image_results = gemini_websearch.search_images(f"{query} medical research diagram", num_results=1)
        if image_results and len(image_results) > 0:
            image_url = image_results[0].get('link')
            if image_url:
                _pdf_add_image(pdf, image_url, width=150)
    except Exception as e:
        print(f"Failed to add summary image: {e}")

    # Key Findings (dynamic counts)
    patents_key = next((k for k in data.keys() if k.lower().startswith('patent')), None)
    trials_key = next((k for k in data.keys() if 'trial' in k.lower()), None)
    exim_key = next((k for k in data.keys() if 'exim' in k.lower()), None)
    web_key = next((k for k in data.keys() if 'web' in k.lower()), None)
    iqvia_key = next((k for k in data.keys() if 'iqvia' in k.lower()), None)
    def _count(k):
        v = data.get(k) if k else None
        return len(v) if isinstance(v, list) else (1 if v else 0)
    _pdf_add_section(pdf, "Key Findings")
    findings = [
        f"Recent patent activity indicates innovation ({_count(patents_key)} items)",
        f"Clinical trials show active research ({_count(trials_key)} studies)",
        f"Trade intelligence available ({_count(exim_key)} partners)",
        f"Web search insights collected ({_count(web_key)} results)",
        f"Market stats and trends analyzed ({'yes' if iqvia_key else 'no'})",
    ]
    _pdf_add_text(pdf, findings)

    # Data Analysis header
    _pdf_add_section(pdf, "Data Analysis")
    _pdf_add_text(pdf, "Detailed sections follow with tables, charts, and relevant images where applicable.")
    
    for section, content in data.items():
        _pdf_add_section(pdf, section)
        
        # Add an image related to this section
        try:
            image_query = f"{query} {section} medical illustration"
            if 'patent' in section.lower():
                image_query = f"{query} patent research diagram"
            elif 'trial' in section.lower():
                image_query = f"{query} clinical trial process"
            elif 'exim' in section.lower():
                image_query = f"{query} trade data visualization"
            
            image_results = gemini_websearch.search_images(image_query, num_results=1)
            if image_results and len(image_results) > 0:
                image_url = image_results[0].get('link')
                if image_url:
                    _pdf_add_image(pdf, image_url, width=130)
        except Exception as e:
            print(f"Failed to add section image for {section}: {e}")
        
        if isinstance(content, list) and content:
            # Use table for list of dicts; if nested dict values, flatten for readability
            if all(isinstance(item, dict) for item in content):
                # Flatten nested dicts lightly for table cells
                flattened = []
                for item in content:
                    flat = {}
                    for k, v in item.items():
                        if isinstance(v, dict):
                            flat[k] = ", ".join(f"{sk}:{sv}" for sk, sv in v.items())
                        elif isinstance(v, list):
                            flat[k] = ", ".join(str(x) for x in v[:5])
                        else:
                            flat[k] = v
                    flattened.append(flat)
                _pdf_add_table(pdf, flattened)
            else:
                for item in content:
                    _pdf_add_text(pdf, item)
            # Dynamic chart: apply rules, draw pie if categorical, else bar
            try:
                for rule in CHART_RULES:
                    out = rule(section, content)
                    if out:
                        labels, values, title = out
                        if labels and values:
                            if len(labels) <= 8 and all(isinstance(v, (int, float)) for v in values):
                                _pdf_add_pie_chart(pdf, title, labels, values)
                            else:
                                _pdf_add_chart(pdf, title, labels, values)
                        break
            except Exception:
                pass
        elif isinstance(content, dict):
            _pdf_add_text(pdf, content)
            # If dict contains image url fields, try to add one
            img_url = None
            for k in ['image', 'image_url', 'thumbnail', 'thumbnail_url']:
                if isinstance(content.get(k), str) and content.get(k).startswith('http'):
                    img_url = content.get(k)
                    break
            if img_url:
                _pdf_add_image(pdf, img_url)
        else:
            _pdf_add_text(pdf, content)
        pdf.ln()

    pdf.output(filepath)
    return filepath

def generate_excel_report(query, data, filename=None):
    """Generate an Excel report from the given data."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.xlsx"
    # Build absolute path in OUTPUT_DIR
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Add a cover sheet with report information
        cover_data = {
            'Report Title': [f"Pharma Research Report: {str(query or '').strip() or 'Pharmaceutical'}"],
            'Generated On': [datetime.now().strftime("%B %d, %Y at %H:%M")],
            'Sections': [len(data)],
        }
        cover_df = pd.DataFrame(cover_data)
        cover_df.to_excel(writer, sheet_name='Report Info', index=False)
        
        # Process each section
        for section, content in data.items():
            sheet = section[:31] if section else 'Sheet'
            if isinstance(content, list) and content:
                # Flatten nested dicts and avoid raw JSON columns
                flattened = []
                for item in content:
                    if isinstance(item, dict):
                        flat = {}
                        for k, v in item.items():
                            if isinstance(v, dict):
                                flat[k] = ", ".join(f"{sk}:{sv}" for sk, sv in v.items())
                            elif isinstance(v, list):
                                flat[k] = ", ".join(str(x) for x in v[:10])
                            else:
                                flat[k] = v
                        flattened.append(flat)
                    else:
                        flattened.append({"value": item})
                df = pd.DataFrame(flattened)
            elif isinstance(content, dict):
                # Flatten top-level dict into a single row
                flat = {}
                for k, v in content.items():
                    if isinstance(v, dict):
                        flat[k] = ", ".join(f"{sk}:{sv}" for sk, sv in v.items())
                    elif isinstance(v, list):
                        flat[k] = ", ".join(str(x) for x in v[:10])
                    else:
                        flat[k] = v
                df = pd.DataFrame([flat])
            else:
                df = pd.DataFrame([{"value": content}])
            
            # Apply formatting to improve readability
            if not df.empty:
                # Limit columns for readability
                df = df.iloc[:, :20]  # Limit to first 20 columns
                
                # Write to Excel with formatting
                df.to_excel(writer, sheet_name=sheet, index=False)
                
                # Get the worksheet to apply formatting
                worksheet = writer.sheets[sheet]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Max width of 50
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
    return filepath

def generate_text_summary(query, data):
    """Generate a text summary from the given data."""
    summary = f"Summary for: {query}\n\n"
    for section, content in data.items():
        summary += f"--- {section} ---\n"
        if isinstance(content, list) and content:
            summary += f"Found {len(content)} items.\n"
        elif content:
            summary += "Details available.\n"
        else:
            summary += "No data found.\n"
        summary += "\n"
    return summary


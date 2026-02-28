from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os

def generate_individual_report(employee, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor("#3B82F6"))
    elements.append(Paragraph(f"Attendance Report: {employee['name']}", title_style))
    elements.append(Paragraph(f"ID: {employee['id']} | Dept: {employee['dept']}", styles['Normal']))
    elements.append(Spacer(1, 20))
    summary_data = [
        ["Stat", "Value"],
        ["Attendance %", f"{employee.get('attendance_pct', 0)}%"],
        ["Actual Hours", f"{employee.get('actual_hours', 0)}h"],
        ["Target Hours", f"{employee.get('target_hours', 0)}h"],
        ["Days Present", str(employee.get('days_present', 0))],
        ["Status", employee.get('status', 'Unknown')]
    ]
    t = Table(summary_data, colWidths=[150, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Day-by-Day Attendance", styles['Heading2']))
    record_data = [["Date", "In", "Out", "Total", "Status"]]
    for r in employee['records']:
        status = "Present" if r['total'] != "00:00" else "Anomaly"
        record_data.append([r['date'], r['in'], r['out'], r['total'], status])
    rt = Table(record_data, colWidths=[100, 80, 80, 80, 80])
    rt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(rt)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("ML Insights & Patterns", styles['Heading2']))
    elements.append(Paragraph(f"Detected Pattern: {employee.get('pattern', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"Risk Score: {employee.get('risk_score', 0)}/100", styles['Normal']))
    doc.build(elements)
    return filepath
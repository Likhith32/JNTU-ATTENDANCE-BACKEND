import pdfplumber
import re
from datetime import datetime
import pandas as pd

def parse_attendance_pdf(file_path):
    all_data = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            lines = text.split("\n")
            current_employee = None
            for line in lines:
                # 1. Look for Employee Info (Multiple patterns)
                # Pattern A: Employee Name: Name, EmployeeID: ID
                # Pattern B: Name: Name ID: ID
                # Pattern C: Emp. Name: Name ...
                emp_patterns = [
                    r"(?:Employee\s+)?Name[:\s\-]+(.*?)(?:,|\s+)(?:Employee\s*)?ID[:\s\-]+(\w+)",
                    r"Name[:\s\-]+(.*?)\s+ID[:\s\-]+(\w+)",
                    r"Emp\s*[:\s\-]+(.*?)\s+ID\s*[:\s\-]+(\w+)"
                ]
                
                emp_match = None
                for p in emp_patterns:
                    emp_match = re.search(p, line, re.I)
                    if emp_match: break
                
                if emp_match:
                    current_employee = {
                        "name": emp_match.group(1).strip(),
                        "id": emp_match.group(2).strip(),
                        "dept": "General",
                        "records": []
                    }
                    # Try to find department in the same or nearby lines
                    dept_match = re.search(r"(?:Dept|Department)[:\s\-]+(\w+)", line, re.I)
                    if dept_match: current_employee["dept"] = dept_match.group(1).strip()
                    all_data.append(current_employee)
                    continue

                # 2. Look for Attendance Records (Date + Times)
                # Matches DD-MM-YYYY or DD/MM/YYYY or DD-MMM-YYYY
                date_match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4}|\d{2}[-/][A-Z]{3}[-/]\d{4})", line, re.I)
                
                if date_match and current_employee:
                    date_str = date_match.group(1)
                    # Extract all time patterns (HH:MM or HH:MM:SS)
                    times = re.findall(r"(\d{1,2}:\d{2}(?::\d{2})?)", line)
                    
                    if len(times) >= 2: # At least In and Out
                        in_time = times[0]
                        out_time = times[-2] if len(times) >= 3 else times[1]
                        total_time = times[-1] if len(times) >= 3 else "00:00" # Fallback
                        
                        # Sometimes Total is not provided, calculate it if possible? 
                        # For now, stick to extraction but be more flexible with indices
                        if len(times) == 2:
                            # If only 2 times, assume In and Out, Total is 00:00 or handle later
                            total_time = "00:00" 
                        elif len(times) >= 3:
                            # Standard format: IN, OUT, TOTAL (or multiple punches)
                            # We take first as IN, last as TOTAL (usually), pen-ultimate as OUT
                            total_time = times[-1]
                            out_time = times[-2]

                        current_employee["records"].append({
                            "date": date_str,
                            "in": in_time,
                            "out": out_time,
                            "total": total_time
                        })
    return all_data

def calculate_metrics(employees, working_days=25, hours_per_day=8):
    target_hours = working_days * hours_per_day
    results = []
    for emp in employees:
        valid_records = [r for r in emp["records"] if r["total"] != "00:00" and r["total"] != "00:00:00"]
        actual_minutes = 0
        arrival_minutes = []
        departure_minutes = []
        for r in valid_records:
            h, m = map(int, r["total"].split(":")[0:2])
            actual_minutes += h * 60 + m
            ah, am = map(int, r["in"].split(":")[0:2])
            arrival_minutes.append(ah * 60 + am)
            dh, dm = map(int, r["out"].split(":")[0:2])
            departure_minutes.append(dh * 60 + dm)
        actual_hours = actual_minutes / 60
        attendance_pct = min((actual_hours / target_hours) * 100, 100.0) if target_hours > 0 else 0
        days_present = len(valid_records)
        anomaly_days = len(emp["records"]) - days_present
        avg_arrival = ""
        if arrival_minutes:
            avg_a_min = sum(arrival_minutes) // len(arrival_minutes)
            avg_arrival = f"{avg_a_min // 60:02d}:{avg_a_min % 60:02d}"
        avg_departure = ""
        if departure_minutes:
            avg_d_min = sum(departure_minutes) // len(departure_minutes)
            avg_departure = f"{avg_d_min // 60:02d}:{avg_d_min % 60:02d}"
        late_days = sum(1 for r in valid_records if int(r["in"].split(":")[0]) >= 10)
        early_leave = sum(1 for r in valid_records if int(r["out"].split(":")[0]) < 17)
        results.append({
            "name": emp["name"],
            "id": emp["id"],
            "dept": emp["dept"],
            "actual_hours": round(actual_hours, 2),
            "target_hours": target_hours,
            "attendance_pct": round(attendance_pct, 1),
            "days_present": days_present,
            "days_absent": working_days - days_present,
            "anomaly_days": anomaly_days,
            "shortfall_hours": round(target_hours - actual_hours, 2),
            "avg_arrival": avg_arrival,
            "avg_departure": avg_departure,
            "late_days": late_days,
            "early_leave_days": early_leave,
            "records": emp["records"]
        })
    return results
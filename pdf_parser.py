from PyPDF2 import PdfReader
import re

def parse_attendance_pdf(file_path):
    all_data = []
    reader = PdfReader(file_path)
    current_employee = None

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        # ✅ ADD THIS - print first 2 pages raw text to see exact format
        if page_num < 2:
            print(f"\n===== PAGE {page_num} RAW TEXT =====")
            for i, line in enumerate(text.split("\n")):
                print(f"  LINE {i:03d}: '{line}'")
            print("=" * 50)

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # -------------------------------------------------------
            # EMPLOYEE HEADER DETECTION
            # Format: "Employee Name : NARAYANA RAO GANTEDA , Employee ID : 1002, Gender : , Department : Out Sourcing, Position : position"
            # -------------------------------------------------------
            emp_match = re.search(
                r"Employee\s+Name\s*:\s*(.+?)\s*,\s*Employee\s+ID\s*:\s*(\d+)",
                line, re.IGNORECASE
            )
            if emp_match:
                name = emp_match.group(1).strip()
                emp_id = emp_match.group(2).strip()

                # Department: stop before ", Position"
                dept = "General"
                dept_match = re.search(
                    r"Department\s*:\s*(.+?)(?:\s*,\s*Position|\s*$)",
                    line, re.IGNORECASE
                )
                if dept_match:
                    dept = dept_match.group(1).strip()

                current_employee = {
                    "name": name,
                    "id": emp_id,
                    "dept": dept,
                    "records": []
                }
                all_data.append(current_employee)
                continue

            # -------------------------------------------------------
            # ATTENDANCE ROW DETECTION
            # Format: "26-01-2026 Monday 08:04 10:30 02:26"
            # Columns: Date | Weekday | First Punch | Last Punch | Total Time
            # (IN Temp and OUT Temp columns are always empty — ignored)
            # -------------------------------------------------------
            date_match = re.match(r"^(\d{2}-\d{2}-\d{4})\b", line)
            if date_match and current_employee is not None:
                date_str = date_match.group(1)

                # Extract all HH:MM time patterns from the line
                # \b boundary ensures we don't match partial numbers
                times = re.findall(r"\b(\d{1,2}:\d{2})\b", line)

                if len(times) >= 3:
                    # Best case: First Punch, Last Punch, Total Time all present
                    in_time    = times[0]
                    out_time   = times[1]
                    total_time = times[2]

                elif len(times) == 2:
                    # Total Time missing — calculate from First and Last Punch
                    in_time  = times[0]
                    out_time = times[1]
                    try:
                        ih, im = map(int, in_time.split(":"))
                        oh, om = map(int, out_time.split(":"))
                        diff_mins = (oh * 60 + om) - (ih * 60 + im)
                        diff_mins = max(diff_mins, 0)
                        total_time = f"{diff_mins // 60:02d}:{diff_mins % 60:02d}"
                    except Exception:
                        total_time = "00:00"

                elif len(times) == 1:
                    # Single punch only (like "17:14 17:14 00:00" anomaly rows)
                    in_time    = times[0]
                    out_time   = times[0]
                    total_time = "00:00"

                else:
                    # No punches at all — absent day
                    in_time    = "00:00"
                    out_time   = "00:00"
                    total_time = "00:00"

                current_employee["records"].append({
                    "date":  date_str,
                    "in":    in_time,
                    "out":   out_time,
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
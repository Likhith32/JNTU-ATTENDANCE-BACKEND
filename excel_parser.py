import pandas as pd
import re
from datetime import datetime

def parse_attendance_xlsx(file_path):
    """
    Parses a JNTUGV biometric Excel export.
    Returns a list of dictionaries with employee info and attendance records.
    """
    all_employees = []
    
    try:
        # Read all sheets as strings to avoid automatic time/date conversion issues
        # sheet_name=None returns a dictionary of dataframes {sheet_name: df}
        xlsx_dict = pd.read_excel(file_path, sheet_name=None, header=None, dtype=str)
        
        for sheet_name, df in xlsx_dict.items():
            # Drop completely empty rows and columns to simplify scanning
            df = df.dropna(how='all').reset_index(drop=True)
            
            current_employee = None
            
            for index, row in df.iterrows():
                val_a = str(row[0]).strip() if pd.notna(row[0]) else ""
                
                # 1. Detect Employee Info Row (Row 6 style merged cell)
                if "Employee Name" in val_a:
                    # Regex patterns as specified
                    name_match = re.search(r"Employee\s*Name\s*[:\-]\s*([^,]+?)(?:\s*,\s*Employee)", val_a, re.I)
                    id_match   = re.search(r"Employee\s*ID\s*[:\-]\s*(\w+)", val_a, re.I)
                    dept_match = re.search(r"Department\s*[:\-]\s*([^,\n]+)", val_a, re.I)
                    
                    if name_match and id_match:
                        current_employee = {
                            "name": name_match.group(1).strip(),
                            "id": id_match.group(1).strip(),
                            "dept": dept_match.group(1).strip() if dept_match else "General",
                            "records": []
                        }
                        all_employees.append(current_employee)
                    continue
                
                # 2. Extract Attendance Records
                # Column B (index 1) contains the date in DD-MM-YYYY format
                val_b = str(row[1]).strip() if pd.notna(row[1]) else ""
                if re.match(r"\d{2}-\d{2}-\d{4}", val_b):
                    if current_employee is not None:
                        # Helper to format time strings
                        def format_time(val):
                            if pd.isna(val) or str(val).lower() == "nan" or not str(val).strip():
                                return "00:00"
                            s_val = str(val).strip()
                            # If it's a full ISO timestamp or similar, take HH:MM
                            if " " in s_val: # e.g. "2026-01-25 07:40:00"
                                try:
                                    return s_val.split(" ")[1][:5]
                                except:
                                    pass
                            return s_val[:5]

                        rec = {
                            "date": val_b,
                            "in": format_time(row[3]),    # Column D: First Punch
                            "out": format_time(row[4]),   # Column E: Last Punch
                            "total": format_time(row[5])  # Column F: Total Time
                        }
                        current_employee["records"].append(rec)
                        
    except Exception as e:
        print(f"Error parsing Excel file {file_path}: {e}")
        raise e
        
    return all_employees

if __name__ == "__main__":
    # Quick internal test with manual data if needed
    pass

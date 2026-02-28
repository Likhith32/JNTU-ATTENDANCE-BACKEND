import pandas as pd
import os
from excel_parser import parse_attendance_xlsx

def create_mock_excel(file_path):
    # Create a mock Excel file matching the JNTUGV structure
    data = [
        ["First & Last Report", None, None, None, None, None, None, None],
        ["From  January 25 2026  To  February 25 2026", None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None],
        ["Company : JNTUGV", None, None, None, None, None, "28-02-2026 20:13", None],
        [None, None, None, None, None, None, None, None],
        ["Employee Name : SHINAGAM SANTHOSH KUMAR , Employee ID : 5002, Gender : , Department : General", None, None, None, None, None, None, None],
        ["No.", "Date", "Weekday", "First Punch", "Last Punch", "Total Time", "IN Temp", "OUT Temp"],
        ["1", "25-01-2026", "Sunday", "07:40", "17:53", "10:13", None, None],
        ["2", "26-01-2026", "Monday", "07:07", "16:22", "09:16", None, None],
        ["3", "01-02-2026", "Sunday", "19:01", "19:01", "00:00", None, None],
        [None, None, None, None, None, None, None, None],
        ["Employee Name : TEST USER , Employee ID : 5003, Gender : , Department : CSE", None, None, None, None, None, None, None],
        ["No.", "Date", "Weekday", "First Punch", "Last Punch", "Total Time", "IN Temp", "OUT Temp"],
        ["1", "25-01-2026", "Sunday", "08:00", "17:00", "09:00", None, None],
    ]
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False, header=False)

def test_parser():
    test_file = "test_attendance.xlsx"
    create_mock_excel(test_file)
    try:
        results = parse_attendance_xlsx(test_file)
        print(f"Detected {len(results)} employees")
        for emp in results:
            print(f"Employee: {emp['name']} ({emp['id']}) - Dept: {emp['dept']}")
            print(f"  Records: {len(emp['records'])}")
            for rec in emp['records']:
                print(f"    {rec['date']}: IN {rec['in']}, OUT {rec['out']}, TOTAL {rec['total']}")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_parser()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
from pdf_parser import parse_attendance_pdf, calculate_metrics
from excel_parser import parse_attendance_xlsx
from email_service import send_low_attendance_alert
from ml_model import generate_ml_insights
import json
from report_generator import generate_individual_report

app = Flask(__name__)

CORS(
    app,
    origins=[
        "http://localhost:5173",
        "https://attendance-pro-clyc.vercel.app"
    ],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data.json'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_store():
    if not os.path.exists(DATA_FILE):
        return {
            "raw_data": [],
            "calculated_results": [],
            "last_params": {"working_days": 25, "hours_per_day": 8}
        }
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "raw_data": [],
            "calculated_results": [],
            "last_params": {"working_days": 25, "hours_per_day": 8}
        }

def save_store(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

STORE = load_store()


# ─────────────────────────────────────────────
# UPLOAD PDF
# ─────────────────────────────────────────────
@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
    file.save(file_path)
    try:
        data = parse_attendance_pdf(file_path)
        if not data:
            return jsonify({"error": "Could not parse any employees from PDF. Check PDF format."}), 422
        STORE["raw_data"] = data
        STORE["calculated_results"] = []
        return jsonify({
            "message": "Upload successful",
            "employees_detected": len(data),
            "pages": "All"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# UPLOAD EXCEL
# ─────────────────────────────────────────────
@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"error": "Invalid file type. Please upload an Excel file."}), 400

    file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{file.filename}")
    file.save(file_path)
    try:
        data = parse_attendance_xlsx(file_path)
        if not data:
            return jsonify({"error": "Could not parse any employees from Excel. Check file structure."}), 422
        STORE["raw_data"] = data
        STORE["calculated_results"] = []
        return jsonify({
            "message": "Excel upload successful",
            "employees_detected": len(data),
            "sheets": "All"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# CALCULATE METRICS + ML
# ─────────────────────────────────────────────
@app.route('/api/calculate', methods=['POST'])
def calculate():
    params = request.json or {}
    working_days = int(params.get("working_days", 25))
    hours_per_day = int(params.get("hours_per_day", 8))
    STORE["last_params"] = {"working_days": working_days, "hours_per_day": hours_per_day}

    if not STORE["raw_data"]:
        return jsonify({"error": "No data available. Please upload a PDF first."}), 400

    try:
        results = calculate_metrics(STORE["raw_data"], working_days, hours_per_day)
        insights = generate_ml_insights(results)
        STORE["calculated_results"] = insights
        save_store(STORE)

        recipient_email = params.get("recipient_email", "")
        alert_res = send_low_attendance_alert(insights, recipient_email)
        print(f"[AUTO-ALERT] Result: {alert_res}")

        return jsonify(insights), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# SEND MANUAL ALERT
# ─────────────────────────────────────────────
@app.route('/api/send-alert', methods=['POST'])
def send_alert():
    if not STORE["calculated_results"]:
        return jsonify({"error": "No results available. Please upload and calculate first."}), 400

    params = request.json or {}
    recipient_email = params.get("recipient_email", "")
    res = send_low_attendance_alert(STORE["calculated_results"], recipient_email)
    return jsonify(res), 200


# ─────────────────────────────────────────────
# TEST EMAIL
# ─────────────────────────────────────────────
@app.route('/api/test-email', methods=['POST'])
def test_email():
    params = request.json or {}
    recipient = params.get("recipient_email", "")

    test_data = [{
        "name": "TEST SYSTEM ALERT", "id": "TEST-001", "dept": "N/A",
        "attendance_pct": 25.0, "risk_score": 95, "pattern": "System Test"
    }]

    res = send_low_attendance_alert(test_data, recipient)
    return jsonify(res), 200


# ─────────────────────────────────────────────
# GET ALL RESULTS
# ─────────────────────────────────────────────
@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify(STORE["calculated_results"]), 200


# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
@app.route('/api/summary', methods=['GET'])
def get_summary():
    if not STORE["calculated_results"]:
        return jsonify({
            "total_employees": 0,
            "avg_attendance": 0,
            "best_performer": {"name": "N/A", "att": 0},
            "worst_performer": {"name": "N/A", "att": 0},
            "anomaly_cases": 0,
            "status_distribution": {
                "Exceptional": 0,
                "Excellent": 0,
                "Good": 0,
                "Warning": 0,
                "Critical": 0,
                "Severe": 0
            },
            "ready": False
        }), 200

    res = STORE["calculated_results"]
    best = max(res, key=lambda x: x["attendance_pct"])
    worst = min(res, key=lambda x: x["attendance_pct"])

    return jsonify({
        "total_employees": len(res),
        "avg_attendance": round(sum(r["attendance_pct"] for r in res) / len(res), 1),
        "best_performer": {"name": best["name"], "att": best["attendance_pct"]},
        "worst_performer": {"name": worst["name"], "att": worst["attendance_pct"]},
        "anomaly_cases": sum(1 for r in res if r.get("anomaly_flag")),
        "status_distribution": {
            "Exceptional": sum(1 for r in res if r.get("status") == "Exceptional"),
            "Excellent":   sum(1 for r in res if r.get("status") == "Excellent"),
            "Good":        sum(1 for r in res if r.get("status") == "Good"),
            "Warning":     sum(1 for r in res if r.get("status") == "Warning"),
            "Critical":    sum(1 for r in res if r.get("status") == "Critical"),
            "Severe":      sum(1 for r in res if r.get("status") == "Severe"),
        },
        "ready": True
    }), 200


# ─────────────────────────────────────────────
# DOWNLOAD INDIVIDUAL REPORT
# ─────────────────────────────────────────────
@app.route('/api/download-report/<emp_id>', methods=['GET'])
def download_report(emp_id):
    emp = next((e for e in STORE["calculated_results"] if str(e["id"]).strip() == str(emp_id).strip()), None)
    if not emp:
        available_ids = [str(e["id"]) for e in STORE["calculated_results"]]
        print(f"[DEBUG] Employee {emp_id} not found. Available IDs: {available_ids}")
        return jsonify({"error": f"Employee ID {emp_id} not found. Total results in memory: {len(STORE['calculated_results'])}"}), 404
    try:
        filepath = os.path.join(UPLOAD_FOLDER, f"report_{emp_id}.pdf")
        generate_individual_report(emp, filepath)
        return send_file(filepath, as_attachment=True, download_name=f"Report_{emp_id}_{emp['name']}.pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# BULK EXPORT — ZIP of all PDFs + Excel
# ─────────────────────────────────────────────
@app.route('/api/export-bulk', methods=['GET'])
def export_bulk():
    if not STORE["calculated_results"]:
        return jsonify({"error": "No data to export. Upload and calculate first."}), 400

    import zipfile
    import pandas as pd
    from io import BytesIO

    try:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
            for emp in STORE["calculated_results"]:
                report_path = os.path.join(UPLOAD_FOLDER, f"temp_{emp['id']}.pdf")
                generate_individual_report(emp, report_path)
                zip_file.write(report_path, f"reports/Report_{emp['id']}_{emp['name']}.pdf")
                if os.path.exists(report_path):
                    os.remove(report_path)

            df = pd.DataFrame(STORE["calculated_results"])
            if 'records' in df.columns:
                df = df.drop(columns=['records'])
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False)
            zip_file.writestr("Attendance_Summary.xlsx", excel_buffer.getvalue())

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='Attendance_Bulk_Export.zip'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# ML INSIGHTS ENDPOINT
# ─────────────────────────────────────────────
@app.route('/api/ml-insights', methods=['GET'])
def ml_insights():
    return jsonify(STORE["calculated_results"]), 200


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "employees_loaded": len(STORE["raw_data"]),
        "results_ready": len(STORE["calculated_results"]) > 0
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

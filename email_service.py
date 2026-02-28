import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

# Load variables from .env relative to this file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

def send_low_attendance_alert(employees: list, recipient_email: str = ""):
    """
    Filters employees with < 50% attendance and sends an HTML email alert.
    """
    # 1. Load credentials with fallbacks
    sender_email = os.getenv("SMTP_SENDER", "yourgmail@gmail.com")
    password = os.getenv("SMTP_PASSWORD", "")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@jntugv.ac.in")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    
    # Use provided recipient_email if valid, otherwise fallback to admin_email
    target_email = recipient_email.strip() if recipient_email and "@" in str(recipient_email) else admin_email
    try:
        smtp_port = int(os.getenv("SMTP_PORT", 587))
    except ValueError:
        smtp_port = 587

    # 2. Filter employees below 50%
    print(f"[DEBUG EMAIL] Total employees to check: {len(employees)}")
    flagged = [e for e in employees if e.get("attendance_pct", 0) < 50]
    
    is_summary = False
    if not flagged:
        print("[DEBUG EMAIL] No employees below 50%. Taking lowest 5 as summary.")
        # Sort by attendance ascending and take top 5
        sorted_emp = sorted(employees, key=lambda x: x.get("attendance_pct", 0))
        flagged = sorted_emp[:5]
        is_summary = True
    
    print(f"[DEBUG EMAIL] Employees in report: {len(flagged)} (Mode: {'Summary' if is_summary else 'Alert'})")

    if not flagged:
        print("[DEBUG EMAIL] No employee data available at all. Skipping email.")
        return {"sent": False, "reason": "No employee data available", "flagged_count": 0}

    print(f"[DEBUG EMAIL] Target recipient: {target_email}")
    print(f"[DEBUG EMAIL] SMTP Host: {smtp_host}:{smtp_port}")
    if not password:
        print("[DEBUG EMAIL] WARNING: SMTP_PASSWORD is empty!")

    try:
        # 3. Create Message
        subject = f"⚠ JNTUGV Attendance Alert — {len(flagged)} critical (<50%)" if not is_summary else f"📊 JNTUGV Attendance Summary — Lowest {len(flagged)} members"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = target_email

        # 4. Generate Table Rows
        table_rows = ""
        for i, emp in enumerate(flagged, 1):
            att = emp.get("attendance_pct", 0)
            # Red if < 30%, Orange if 30-50%
            bg_color = "#FEE2E2" if att < 30 else "#FFEDD5"
            text_color = "#991B1B" if att < 30 else "#9A3412"
            
            table_rows += f"""
            <tr style="background-color: {bg_color}; color: {text_color};">
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{i}</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{emp.get('name')}</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{emp.get('id')}</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{emp.get('dept')}</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0; font-weight: bold;">{att}%</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{emp.get('risk_score', 'N/A')}</td>
                <td style="padding: 10px; border: 1px solid #E2E8F0;">{emp.get('pattern', 'N/A')}</td>
            </tr>
            """

        # 5. Build HTML Body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1E293B;">
            <div style="max-width: 800px; margin: 0 auto; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden;">
                <div style="background-color: { '#EF4444' if not is_summary else '#6366F1' }; color: white; padding: 20px; text-align: center;">
                    <h2 style="margin: 0;">JNTUGV Biometric Attendance System</h2>
                    <p style="margin: 5px 0 0; opacity: 0.9;">{ 'Low Attendance Alert' if not is_summary else 'Lowest Attendance Summary' }</p>
                </div>
                <div style="padding: 24px;">
                    <p><strong>Date Generated:</strong> {datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
                    <p>{ 'The following employees have been flagged for attendance below 50%:' if not is_summary else 'Below is a summary of the 5 employees with the lowest attendance records:' }</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
                        <thead>
                            <tr style="background-color: #F8FAFC; text-align: left;">
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">No.</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">Name</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">ID</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">Dept</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">Att %</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">Risk</th>
                                <th style="padding: 10px; border: 1px solid #E2E8F0;">Pattern</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
                <div style="background-color: #F8FAFC; padding: 15px; text-align: center; color: #64748B; font-size: 12px; border-top: 1px solid #E2E8F0;">
                    This is an automated alert from JNTUGV Attendance Analytics.
                </div>
            </div>
        </body>
        </html>
        """

        # 6. Plain Text fallback
        msg_header = "JNTUGV Attendance Alert" if not is_summary else "JNTUGV Attendance Summary"
        plain_text = f"{msg_header}\n\nDate: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
        plain_text += f"{ 'Employees below 50% attendance:' if not is_summary else 'Top 5 lowest attendance members:' }\n\n"
        for emp in flagged:
            plain_text += f"- {emp['name']} ({emp['id']}): {emp['attendance_pct']}%\n"

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # 7. Connect and Send
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)

        return {
            "sent": True, 
            "flagged_count": len(flagged), 
            "recipient": target_email,
            "message": "Alert sent successfully"
        }

    except Exception as e:
        print(f"[DEBUG EMAIL] ERROR: {e}")
        return {"sent": False, "error": str(e), "flagged_count": len(flagged)}

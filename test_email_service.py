import unittest
from unittest.mock import patch, MagicMock
from email_service import send_low_attendance_alert

class TestEmailService(unittest.TestCase):

    def test_filter_no_flagged(self):
        # All above 50%
        employees = [{"attendance_pct": 60}, {"attendance_pct": 55}]
        result = send_low_attendance_alert(employees)
        self.assertFalse(result["sent"])
        self.assertEqual(result["reason"], "No employees below 50% threshold")

    @patch("smtplib.SMTP")
    def test_send_alert_success(self, mock_smtp):
        # Mock SMTP connection
        instance = mock_smtp.return_value.__enter__.return_value
        
        employees = [
            {"name": "Low Att 1", "id": "1", "dept": "D1", "attendance_pct": 20},
            {"name": "Low Att 2", "id": "2", "dept": "D2", "attendance_pct": 40},
            {"name": "High Att", "id": "3", "dept": "D3", "attendance_pct": 80},
        ]
        
        result = send_low_attendance_alert(employees)
        
        self.assertTrue(result["sent"])
        self.assertEqual(result["flagged_count"], 2)
        self.assertTrue(instance.starttls.called)
        self.assertTrue(instance.login.called)
        self.assertTrue(instance.send_message.called)

if __name__ == "__main__":
    unittest.main()

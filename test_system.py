"""
Comprehensive Verification and QA Test Suite for Siddhanth Firm Management System
Tests:
- Authentication & Sessions
- Dashboard Metrics & New Testing Cards
- Gold Testing Entry, List, View, Sample Bill & PDF
- Silver Testing Entry, List, View, Sample Bill & PDF
- Existing Modules (Silver Polish, Gold Polish, Jewelry Box, Reports, Settings)
- Global Search API
"""

import unittest
import time
from datetime import date
from app import app
from db import get_db

class SiddhanthFirmExtendedTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Admin"
            sess["role"] = "admin"

    def test_01_dashboard_integration(self):
        """Dashboard renders with Gold & Silver Testing cards and real DB metrics"""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Gold Testing (स्वर्ण टंच)", html)
        self.assertIn("Silver Testing (रजत टंच)", html)
        self.assertIn("New Gold Test", html)
        self.assertIn("New Silver Test", html)
        self.assertIn("Recent Gold Tests", html)
        self.assertIn("Recent Silver Tests", html)
        self.assertIn("7-Day Revenue Overview", html)

    def test_02_gold_testing_list(self):
        """Gold testing records list and search"""
        response = self.client.get("/gold-testing")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Gold Testing Services", html)
        self.assertIn("GT-2026-0149", html)
        self.assertIn("Banshidhar Jewellers", html)

    def test_03_gold_testing_new_entry(self):
        """Add new Gold Testing receipt with multiple items"""
        rec_no = f"GT-TEST-{int(time.time()*1000)}"
        data = {
            "receipt_no": rec_no,
            "customer_name": "Kalyan Jewellers Test",
            "contact_no": "9876543210",
            "address": "Civil Lines, Hardoi",
            "test_date": str(date.today()),
            "payment_method": "UPI",
            "testing_status": "Completed",
            "notes": "Test assay entry",
            "item_name[]": ["Gold Necklace (हार)", "Gold Ring (अंगूठी)"],
            "gross_weight[]": ["24.500", "5.200"],
            "net_weight[]": ["24.500", "5.000"],
            "purity_karat[]": ["22.00", "18.00"],
            "purity_percent[]": ["91.67", "75.00"],
            "fine_gold_weight[]": ["22.459", "3.750"],
            "testing_method[]": ["Computerized XRF Assay", "Computerized XRF Assay"],
            "quantity[]": ["1", "1"],
            "testing_charge[]": ["100.00", "100.00"],
            "total_charge[]": ["100.00", "100.00"],
            "subtotal": "200.00",
            "additional_charges": "0.00",
            "discount": "0.00",
            "grand_total": "200.00",
            "amount_received": "200.00",
            "balance_amount": "0.00"
        }
        response = self.client.post("/gold-testing/new", data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Kalyan Jewellers Test", html)
        self.assertIn(rec_no, html)

        # Verify DB
        conn = get_db()
        test = conn.execute("SELECT * FROM gold_tests WHERE receipt_no = ?", (rec_no,)).fetchone()
        self.assertIsNotNone(test)
        items = conn.execute("SELECT * FROM gold_test_items WHERE test_id = ?", (test["id"],)).fetchall()
        self.assertEqual(len(items), 2)
        conn.close()

    def test_04_gold_testing_sample_bill_and_pdf(self):
        """View Gold sample bill and download PDF"""
        sample_resp = self.client.get("/gold-testing/sample")
        self.assertEqual(sample_resp.status_code, 200)
        html = sample_resp.data.decode("utf-8")
        self.assertIn("श्री सिद्धनाथ बुलियन टंच", html)
        self.assertIn("GOLD ASSAY CERTIFICATE & TAX INVOICE", html)

        conn = get_db()
        test = conn.execute("SELECT id FROM gold_tests LIMIT 1").fetchone()
        conn.close()
        pdf_resp = self.client.get(f"/gold-testing/{test['id']}/pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.mimetype, "application/pdf")
        self.assertGreater(len(pdf_resp.data), 1000)

    def test_05_silver_testing_list(self):
        """Silver testing records list and search"""
        response = self.client.get("/silver-testing")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Silver Testing Services", html)
        self.assertIn("ST-2026-0508", html)
        self.assertIn("Vaibhav Ji Jewellers", html)

    def test_06_silver_testing_new_entry(self):
        """Add new Silver Testing receipt with multiple items"""
        rec_no = f"ST-TEST-{int(time.time()*1000)}"
        data = {
            "receipt_no": rec_no,
            "customer_name": "Agrawal Bullion Test",
            "contact_no": "9123456789",
            "address": "Bada Chauraha, Hardoi",
            "test_date": str(date.today()),
            "payment_method": "Cash",
            "testing_status": "Completed",
            "notes": "Test silver assay",
            "item_name[]": ["Silver Payal (पायल)", "Silver Idol (मूर्ति)"],
            "gross_weight[]": ["85.200", "150.000"],
            "net_weight[]": ["80.000", "150.000"],
            "purity_fineness[]": ["61 | 70", "925 Sterling"],
            "purity_percent[]": ["61.70", "92.50"],
            "testing_method[]": ["Computerized XRF Assay & Touch", "Computerized XRF Assay"],
            "quantity[]": ["1", "1"],
            "testing_charge[]": ["50.00", "50.00"],
            "total_charge[]": ["50.00", "50.00"],
            "subtotal": "100.00",
            "additional_charges": "0.00",
            "discount": "0.00",
            "grand_total": "100.00",
            "amount_received": "100.00",
            "balance_amount": "0.00"
        }
        response = self.client.post("/silver-testing/new", data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        html = response.data.decode("utf-8")
        self.assertIn("Agrawal Bullion Test", html)
        self.assertIn(rec_no, html)

        # Verify DB
        conn = get_db()
        test = conn.execute("SELECT * FROM silver_tests WHERE receipt_no = ?", (rec_no,)).fetchone()
        self.assertIsNotNone(test)
        items = conn.execute("SELECT * FROM silver_test_items WHERE test_id = ?", (test["id"],)).fetchall()
        self.assertEqual(len(items), 2)
        conn.close()

    def test_07_silver_testing_sample_bill_and_pdf(self):
        """View Silver sample bill and download PDF"""
        sample_resp = self.client.get("/silver-testing/sample")
        self.assertEqual(sample_resp.status_code, 200)
        html = sample_resp.data.decode("utf-8")
        self.assertIn("❖ श्री सिद्धनाथ बुलियन टंच ❖", html)
        self.assertIn("SILVER PURITY ASSAY CERTIFICATE & TAX INVOICE", html)

        conn = get_db()
        test = conn.execute("SELECT id FROM silver_tests LIMIT 1").fetchone()
        conn.close()
        pdf_resp = self.client.get(f"/silver-testing/{test['id']}/pdf")
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.mimetype, "application/pdf")
        self.assertGreater(len(pdf_resp.data), 1000)

    def test_08_existing_modules_intact(self):
        """Preserve existing Silver Polish, Gold Polish, Jewelry Box, Reports, and Settings"""
        self.assertEqual(self.client.get("/silver").status_code, 200)
        self.assertEqual(self.client.get("/silver/entry").status_code, 200)
        self.assertEqual(self.client.get("/silver/bills").status_code, 200)
        self.assertEqual(self.client.get("/gold").status_code, 200)
        self.assertEqual(self.client.get("/gold/entry").status_code, 200)
        self.assertEqual(self.client.get("/gold/bills").status_code, 200)
        self.assertEqual(self.client.get("/jewelry").status_code, 200)
        self.assertEqual(self.client.get("/reports").status_code, 200)
        self.assertEqual(self.client.get("/settings").status_code, 200)

    def test_09_api_search_includes_testing(self):
        """Global Search API finds gold and silver testing records"""
        resp = self.client.get("/api/search?q=Banshidhar")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(any("Gold Test" in item["type"] for item in data))

        resp2 = self.client.get("/api/search?q=Vaibhav")
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.get_json()
        self.assertTrue(any("Silver Test" in item["type"] for item in data2))

if __name__ == "__main__":
    unittest.main()

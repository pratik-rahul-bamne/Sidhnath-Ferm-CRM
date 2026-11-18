# 💎 Siddhanth Firm (श्री सिद्धनाथ बुलियन टंच) – Business Management & Billing System

A comprehensive enterprise business management, precious metal assay testing, and billing system for **Silver Polish, Gold Polish, Jewelry Box, Gold Testing (Tunch), and Silver Testing (Tunch)** operations. Built with **Flask + SQLite/PostgreSQL** with professional printable invoices and ReportLab PDF generators.

---

## ✨ Features & Business Operations

| Module | Capabilities |
|---|---|
| 🔬 **Gold Testing Services (स्वर्ण टंच)** | Multi-item gold assay receipts, gross/net weight, Karat (18K, 20K, 22K, 24K), auto-calculated gold purity %, fine gold weight, testing charges, computerized XRF assay certificates, A4 printable bills & PDF download |
| 🧪 **Silver Testing Services (रजत टंच)** | Multi-item silver assay receipts, gross/net weight, fineness / chinha (e.g. 61\|70, 800, 925 Sterling), testing charges, scientific assay certificates, A4 printable bills & PDF download |
| 🥈 **Silver Polish** | Entry/Exit tracking, bill generation (live formula calculation), PDF export |
| 🥇 **Gold Polish** | Entry/Exit tracking, bill generation, PDF export |
| 💍 **Jewelry Box** | Inventory items, customer tracking, sales revenue |
| 📊 **Analytics & Reports** | Combined 5-arm business revenue overview, daily & 30-day interactive Chart.js graphs |
| ⚙️ **Settings & Rates** | Live metal prices per gram + configurable Gold & Silver testing charges (per item/sample), user management |
| 🔐 **Authentication** | Role-based access control (Admin / Staff User) with bcrypt password hashing |

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
copy .env.example .env
```

### 3. Run the Application
```bash
python app.py
```

Visit: **http://localhost:5000**

**Default Admin Credentials:**
- Email: `admin@siddhanth.com`
- Password: `Admin@123`

---

## 🔬 Testing Services & Billing System

### 1. Gold Testing Module (`/gold-testing`)
- **Customer Details**: Name, 10-digit mobile number, address, testing date, auto-generated unique receipt number (`GT-YYYY-XXXX`).
- **Item Details**: Multi-item support under a single certificate. Gross weight, Net weight, Karat purity, Gold %, Fine Gold calculation ($Fine = Net \times \frac{Karat}{24}$), testing method (Computerized XRF Assay, Fire Assay, Touchstone & Acid, Specific Gravity), configurable testing rate.
- **Payment & Totals**: Subtotal, Additional charges, Discount, Grand Total, Amount Received, Balance Due, Payment Mode (Cash, UPI, Bank Transfer, Card).
- **Outputs**:
  - A4 Printable Gold Assay Certificate & Tax Invoice (Direct Print `Ctrl+P`)
  - ReportLab Vector PDF Download (`/gold-testing/<id>/pdf`)
  - Realistic Sample Bill (`/gold-testing/sample`)

### 2. Silver Testing Module (`/silver-testing`)
- **Customer Details**: Name, mobile number, address, testing date, unique receipt number (`ST-YYYY-XXXX`).
- **Item Details**: Multi-item support. Gross weight, Net weight, Purity Fineness / Chinha (e.g., `61 | 70 (617.0 प्रति हजार)`, `800`, `925 Sterling`, `999 Fine Silver`), testing method, quantity, configurable testing charge.
- **Outputs**:
  - A4 Printable Silver Assay Certificate & Tax Invoice (Direct Print `Ctrl+P`)
  - ReportLab Vector PDF Download (`/silver-testing/<id>/pdf`)
  - Realistic Sample Bill (`/silver-testing/sample`)

---

## 💰 Billing Formulas

**Silver Polish:**
$$\text{Total} = (\text{Silver Weight} \times \text{Silver Price}) - \text{Waste} + \text{Extra Weight} + (\text{Silver Gram} \times \text{Gram Price})$$

**Gold Polish:**
$$\text{Total} = (\text{Gold Weight} \times \text{Gold Price}) + (\text{Gold Gram} \times \text{Gram Price})$$

**Testing Services (Gold / Silver):**
$$\text{Subtotal} = \sum (\text{Item Quantity} \times \text{Testing Charge})$$
$$\text{Grand Total} = \text{Subtotal} + \text{Additional Charges} - \text{Discount}$$
$$\text{Remaining Balance} = \text{Grand Total} - \text{Amount Received}$$

---

## 🗃 Database Schema

- `users` – User authentication & roles (Admin, User)
- `rates` – Daily metal prices per gram (Silver, Gold)
- `service_charges` – Configurable service testing rates (`gold_testing`, `silver_testing`)
- `silver_entries` / `silver_bills` – Silver polish records
- `gold_entries` / `gold_bills` – Gold polish records
- `jewelry_items` – Jewelry inventory records
- `gold_tests` – Master receipt for gold testing transactions
- `gold_test_items` – Itemized assay test items per gold test receipt
- `silver_tests` – Master receipt for silver testing transactions
- `silver_test_items` – Itemized assay test items per silver test receipt

---

## 🧪 Testing & Verification

Run the full automated integration test suite:
```bash
python -m unittest test_system.py
```

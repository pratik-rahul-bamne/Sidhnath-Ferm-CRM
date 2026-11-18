-- ============================================================
-- Siddhanth Firm – SQLite Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metal TEXT NOT NULL CHECK (metal IN ('silver', 'gold')),
    price_per_gram REAL NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    silver_weight REAL NOT NULL,
    polish_type TEXT NOT NULL DEFAULT 'without_p' CHECK (polish_type IN ('with_p', 'without_p')),
    contact_no TEXT,
    status TEXT NOT NULL DEFAULT 'entry' CHECK (status IN ('entry', 'exit')),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS silver_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    silver_weight REAL NOT NULL,
    silver_price REAL NOT NULL,
    waste REAL NOT NULL DEFAULT 0,
    extra_weight REAL NOT NULL DEFAULT 0,
    silver_gram REAL NOT NULL DEFAULT 0,
    silver_gram_price REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL,
    contact_no TEXT,
    entry_id INTEGER REFERENCES silver_entries(id),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    gold_weight REAL NOT NULL,
    polish_type TEXT NOT NULL DEFAULT 'without_p' CHECK (polish_type IN ('with_p', 'without_p')),
    contact_no TEXT,
    status TEXT NOT NULL DEFAULT 'entry' CHECK (status IN ('entry', 'exit')),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    gold_weight REAL NOT NULL,
    gold_price REAL NOT NULL,
    gold_gram REAL NOT NULL DEFAULT 0,
    gold_gram_price REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL,
    contact_no TEXT,
    entry_id INTEGER REFERENCES gold_entries(id),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jewelry_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT NOT NULL,
    category TEXT,
    rate REAL NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_price REAL NOT NULL,
    customer_name TEXT,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Service charges / testing rates
CREATE TABLE IF NOT EXISTS service_charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_type TEXT UNIQUE NOT NULL,
    default_rate REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL DEFAULT 'per item',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gold Testing Records
CREATE TABLE IF NOT EXISTS gold_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    contact_no TEXT,
    address TEXT,
    test_date DATE NOT NULL DEFAULT CURRENT_DATE,
    subtotal REAL NOT NULL DEFAULT 0,
    additional_charges REAL NOT NULL DEFAULT 0,
    discount REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    amount_received REAL NOT NULL DEFAULT 0,
    balance_amount REAL NOT NULL DEFAULT 0,
    payment_method TEXT NOT NULL DEFAULT 'Cash' CHECK (payment_method IN ('Cash', 'UPI', 'Bank Transfer', 'Card', 'Other')),
    payment_status TEXT NOT NULL DEFAULT 'Paid' CHECK (payment_status IN ('Paid', 'Partial', 'Unpaid')),
    testing_status TEXT NOT NULL DEFAULT 'Completed' CHECK (testing_status IN ('Completed', 'Pending', 'In-Progress')),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gold Testing Items
CREATE TABLE IF NOT EXISTS gold_test_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES gold_tests(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    gross_weight REAL NOT NULL,
    net_weight REAL,
    purity_karat REAL NOT NULL,
    purity_percent REAL,
    fine_gold_weight REAL,
    testing_method TEXT NOT NULL DEFAULT 'Computerized XRF Assay',
    quantity INTEGER NOT NULL DEFAULT 1,
    testing_charge REAL NOT NULL DEFAULT 100.0,
    total_charge REAL NOT NULL DEFAULT 100.0,
    remarks TEXT
);

-- Silver Testing Records
CREATE TABLE IF NOT EXISTS silver_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    contact_no TEXT,
    address TEXT,
    test_date DATE NOT NULL DEFAULT CURRENT_DATE,
    subtotal REAL NOT NULL DEFAULT 0,
    additional_charges REAL NOT NULL DEFAULT 0,
    discount REAL NOT NULL DEFAULT 0,
    grand_total REAL NOT NULL DEFAULT 0,
    amount_received REAL NOT NULL DEFAULT 0,
    balance_amount REAL NOT NULL DEFAULT 0,
    payment_method TEXT NOT NULL DEFAULT 'Cash' CHECK (payment_method IN ('Cash', 'UPI', 'Bank Transfer', 'Card', 'Other')),
    payment_status TEXT NOT NULL DEFAULT 'Paid' CHECK (payment_status IN ('Paid', 'Partial', 'Unpaid')),
    testing_status TEXT NOT NULL DEFAULT 'Completed' CHECK (testing_status IN ('Completed', 'Pending', 'In-Progress')),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Silver Testing Items
CREATE TABLE IF NOT EXISTS silver_test_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL REFERENCES silver_tests(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    gross_weight REAL NOT NULL,
    net_weight REAL,
    purity_fineness TEXT NOT NULL,
    purity_percent REAL,
    testing_method TEXT NOT NULL DEFAULT 'Computerized XRF Assay',
    quantity INTEGER NOT NULL DEFAULT 1,
    testing_charge REAL NOT NULL DEFAULT 50.0,
    total_charge REAL NOT NULL DEFAULT 50.0,
    remarks TEXT
);

-- Default metal rates
INSERT OR IGNORE INTO rates (metal, price_per_gram) VALUES ('silver', 100.0);
INSERT OR IGNORE INTO rates (metal, price_per_gram) VALUES ('gold', 7000.0);

-- Default testing service charges
INSERT OR IGNORE INTO service_charges (service_type, default_rate, unit, description)
VALUES ('gold_testing', 100.0, 'per item', 'Standard Gold Testing & Computerized Assay');
INSERT OR IGNORE INTO service_charges (service_type, default_rate, unit, description)
VALUES ('silver_testing', 50.0, 'per item', 'Standard Silver Testing & Fineness Assay');

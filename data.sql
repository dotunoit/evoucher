PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE events (
        event_id TEXT PRIMARY KEY,
        event_name TEXT NOT NULL,
        event_date TEXT NOT NULL
    );
CREATE TABLE vendors (
        vendor_id TEXT PRIMARY KEY,
        vendor_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT,
        event_id TEXT NOT NULL, password TEXT,
        FOREIGN KEY (event_id) REFERENCES events(event_id)
    );
CREATE TABLE vouchers (
        voucher_id TEXT PRIMARY KEY,
        voucher_name TEXT NOT NULL,
        email TEXT NOT NULL,
        balance REAL NOT NULL,
        canceled INTEGER DEFAULT 0
    );

CREATE TABLE sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        voucher_id TEXT,
        booth_id TEXT,
        sale_amount REAL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (voucher_id) REFERENCES vouchers(voucher_id),
        FOREIGN KEY (booth_id) REFERENCES vendors(vendor_id)
    );
COMMIT;
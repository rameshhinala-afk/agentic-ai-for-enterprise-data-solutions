"""Creates a small sample enterprise database (SQLite) for the agent to work on."""
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = "enterprise.db"


def create_database(path: str = DB_PATH) -> str:
    random.seed(42)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS orders;

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT, region TEXT, segment TEXT
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT, category TEXT, unit_price REAL, stock INTEGER
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER, product_id INTEGER,
            quantity INTEGER, amount REAL, order_date TEXT
        );
        """
    )

    regions = ["North", "South", "East", "West"]
    segments = ["Enterprise", "SMB", "Startup"]
    customers = [(i, f"Customer {i}", random.choice(regions), random.choice(segments))
                 for i in range(1, 41)]
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)

    catalog = [("Analytics Suite", "Software", 1200), ("Cloud Storage", "Infrastructure", 300),
               ("Security Pack", "Software", 800), ("Edge Gateway", "Hardware", 950),
               ("Support Plan", "Services", 400), ("Data Connector", "Software", 150)]
    products = [(i + 1, n, c, p, random.randint(2, 120)) for i, (n, c, p) in enumerate(catalog)]
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)

    start = date(2026, 1, 1)
    orders = []
    for oid in range(1, 501):
        cust = random.randint(1, 40)
        prod = random.choice(products)
        qty = random.randint(1, 10)
        if oid in (77, 301):  # planted anomalies
            qty = 200
        d = start + timedelta(days=random.randint(0, 300))
        orders.append((oid, cust, prod[0], qty, round(qty * prod[3], 2), d.isoformat()))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)

    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    print("Created", create_database())

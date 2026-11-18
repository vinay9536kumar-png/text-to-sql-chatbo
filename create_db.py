import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "company.db")

conn = sqlite3.connect(DB_PATH)
conn.executescript("""
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    dept_name TEXT PRIMARY KEY,
    location TEXT
);

CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary INTEGER,
    joining_date TEXT,
    FOREIGN KEY (department) REFERENCES departments (dept_name)
);
""")

conn.executemany(
    "INSERT INTO departments VALUES (?, ?)",
    [
        ("IT", "Bengaluru"),
        ("HR", "Delhi"),
        ("Sales", "Mumbai"),
        ("Finance", "Pune"),
    ],
)

conn.executemany(
    "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
    [
        (1, "Rahul", "IT", 45000, "2023-01-10"),
        (2, "Priya", "HR", 38000, "2022-06-15"),
        (3, "Amit", "IT", 52000, "2021-03-01"),
        (4, "Sneha", "Sales", 41000, "2024-02-20"),
        (5, "Vikram", "Sales", 47000, "2023-09-05"),
        (6, "Neha", "Finance", 60000, "2020-07-01"),
        (7, "Rohit", "IT", 61000, "2019-11-15"),
        (8, "Kavya", "Sales", 39000, "2024-05-10"),
    ],
)

conn.commit()
count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
conn.close()
print(f"Database ready: {DB_PATH}")
print(f"Employees inserted: {count}")

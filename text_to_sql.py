import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from google import genai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit(f"GEMINI_API_KEY nahi mili. Ye file check karo: {BASE_DIR}\\.env")

client = genai.Client(api_key=api_key)
MODEL = "gemini-3.8-flash"
DB_PATH = os.path.join(BASE_DIR, "company.db")

# Words that must never appear in a query, so the bot can only read data
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|truncate|vacuum)\b",
    re.IGNORECASE,
)


def ask_gemini(prompt):
    return client.models.generate_content(model=MODEL, contents=prompt).text.strip()


def get_schema(conn):
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND sql IS NOT NULL"
    ).fetchall()
    return "\n\n".join(r[0] for r in rows)


def clean_sql(text):
    # Remove markdown code fences if the model adds them
    text = re.sub(r"^```(?:sql)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_sql(question, schema):
    prompt = (
        "You are an expert in SQLite. Here is the database schema:\n\n"
        f"{schema}\n\n"
        "Write ONE read-only SQLite SELECT query that answers the question below. "
        "Use only the tables and columns in the schema. "
        "Return only the SQL, with no explanation and no markdown.\n\n"
        f"Question: {question}"
    )
    return clean_sql(ask_gemini(prompt))


def check_safety(sql):
    cleaned = sql.strip().rstrip(";").strip()
    if ";" in cleaned:
        return False, "Ek se zyada statement allowed nahi hain."
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        return False, "Sirf SELECT query allowed hai."
    if FORBIDDEN.search(cleaned):
        return False, "Query mein unsafe keyword hai."
    return True, cleaned


def explain_result(question, columns, rows):
    prompt = (
        f"Question: {question}\n"
        f"Columns: {columns}\n"
        f"Rows (up to 20): {rows[:20]}\n\n"
        "Answer the question in one or two short sentences, in the same language "
        "as the question (Hindi or English). Use only the data given."
    )
    return ask_gemini(prompt)


def answer(question, conn, schema):
    sql = generate_sql(question, schema)
    print(f"\nSQL: {sql}")

    ok, result = check_safety(sql)
    if not ok:
        print(f"SQL rukh gaya: {result}")
        return

    cursor = conn.execute(result)
    columns = [d[0] for d in cursor.description] if cursor.description else []
    rows = cursor.fetchall()

    print("\n" + " | ".join(columns))
    for row in rows[:20]:
        print(" | ".join(str(v) for v in row))
    if len(rows) > 20:
        print(f"... aur {len(rows) - 20} rows")

    if rows:
        print(f"\nJawab: {explain_result(question, columns, rows)}")
    else:
        print("\nJawab: Is sawal ka koi data nahi mila.")


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit("company.db nahi mili. Pehle `python create_db.py` chalao.")

    # Read-only connection, so the bot cannot change the data
    uri = Path(DB_PATH).as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    schema = get_schema(conn)

    print("Text-to-SQL ready. Band karne ke liye 'exit' likho.")
    print("Examples: 'IT department mein kitne employees hain?', 'sabse zyada salary kiski hai?'\n")

    while True:
        question = input("Sawal: ").strip()
        if question.lower() in ("exit", "quit", ""):
            break
        try:
            answer(question, conn, schema)
        except sqlite3.Error as e:
            print(f"SQL error: {e}")
        except Exception as e:
            print(f"Error: {e}")
        print()

    conn.close()


if __name__ == "__main__":
    main()

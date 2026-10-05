import sqlite3
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Donation tracker", description="This is a sample FastAPI application for tracking donations.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "donations.db"


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL
            )
            """
        )


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


init_db()


@app.get("/")
def home():
    return {"message": "Donation Tracker API is running. Visit /docs to try it."}


class Donation(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="The name of the donor.")
    amount: float = Field(gt=0, description="The amount of the donation. Must be greater than zero.")


def find_donation(conn: sqlite3.Connection, donation_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM donations WHERE id = ?", (donation_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    return row


@app.post("/donations", status_code=201)
def log_donation(donation: Donation):
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO donations (name, amount) VALUES (?, ?)",
            (donation.name, donation.amount),
        )
        new_id = cursor.lastrowid
        row = find_donation(conn, new_id)
        return dict(row)


@app.get("/donations")
def view_donations():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM donations ORDER BY id").fetchall()
        donations = [dict(row) for row in rows]
        total_amount = sum(donation["amount"] for donation in donations)
        return {
            "donations": donations,
            "total_amount": round(total_amount, 2),
            "count": len(donations),
        }


@app.get("/donations/{donation_id}")
def get_donation(donation_id: int):
    with get_connection() as conn:
        return dict(find_donation(conn, donation_id))


@app.put("/donations/{donation_id}")
def update_donation(donation_id: int, updated_donation: Donation):
    with get_connection() as conn:
        find_donation(conn, donation_id)
        conn.execute(
            "UPDATE donations SET name = ?, amount = ? WHERE id = ?",
            (updated_donation.name, updated_donation.amount, donation_id),
        )
        return dict(find_donation(conn, donation_id))


@app.delete("/donations/{donation_id}")
def delete_donation(donation_id: int):
    with get_connection() as conn:
        donation = dict(find_donation(conn, donation_id))
        conn.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
        return {"message": f"Donation with ID {donation_id} has been deleted.", "deleted_donation": donation}

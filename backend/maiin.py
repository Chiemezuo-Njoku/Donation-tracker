import os
from contextlib import contextmanager

import psycopg                          # CHANGED: Postgres driver instead of sqlite3
from psycopg.rows import dict_row       # CHANGED: makes rows come back as dicts
from dotenv import load_dotenv          # NEW: reads a local .env file
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# NEW: Load variables from a .env file in this folder (only matters locally).
# On Render there's no .env file; you set the variables in its dashboard,
# and this line just does nothing.
load_dotenv()

# NEW: The database address comes from an environment variable instead of
# being written in the code. This keeps your password out of GitHub.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to backend/.env or Render's settings.")

app = FastAPI(title="Donation tracker", description="This is a sample FastAPI application for tracking donations.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        os.getenv("FRONTEND_URL", ""),  # NEW: your Vercel URL once deployed
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_connection():
    # CHANGED: connect to Postgres using the URL.
    # row_factory=dict_row works like sqlite3.Row, but gives plain dicts.
    # prepare_threshold=None avoids an error some Supabase poolers give
    # with prepared statements. Safe to leave on.
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()  # NEW: undo half-finished changes if something fails
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        # CHANGED: Postgres syntax.
        #   INTEGER PRIMARY KEY AUTOINCREMENT -> SERIAL PRIMARY KEY
        #   REAL                              -> DOUBLE PRECISION
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS donations (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                amount DOUBLE PRECISION NOT NULL
            )
            """
        )


init_db()


@app.get("/")
def home():
    return {"message": "Donation Tracker API is running. Visit /docs to try it."}


class Donation(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="The name of the donor.")
    amount: float = Field(gt=0, description="The amount of the donation. Must be greater than zero.")


def find_donation(conn: psycopg.Connection, donation_id: int) -> dict:
    # CHANGED: Postgres uses %s as the placeholder instead of ?
    row = conn.execute("SELECT * FROM donations WHERE id = %s", (donation_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    return row


@app.post("/donations", status_code=201)
def log_donation(donation: Donation):
    with get_connection() as conn:
        # CHANGED: Postgres doesn't support cursor.lastrowid.
        # RETURNING * hands back the new row (including its id) in the
        # same query, so we don't need a second SELECT.
        row = conn.execute(
            "INSERT INTO donations (name, amount) VALUES (%s, %s) RETURNING *",
            (donation.name, donation.amount),
        ).fetchone()
        return row


@app.get("/donations")
def view_donations():
    with get_connection() as conn:
        donations = conn.execute("SELECT * FROM donations ORDER BY id").fetchall()
        total_amount = sum(donation["amount"] for donation in donations)
        return {
            "donations": donations,
            "total_amount": round(total_amount, 2),
            "count": len(donations),
        }


@app.get("/donations/{donation_id}")
def get_donation(donation_id: int):
    with get_connection() as conn:
        return find_donation(conn, donation_id)


@app.put("/donations/{donation_id}")
def update_donation(donation_id: int, updated_donation: Donation):
    with get_connection() as conn:
        # CHANGED: RETURNING * gives back the updated row. If no row has
        # that id, it returns nothing, so we can check for 404 in one query.
        row = conn.execute(
            "UPDATE donations SET name = %s, amount = %s WHERE id = %s RETURNING *",
            (updated_donation.name, updated_donation.amount, donation_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Donation not found")
        return row


@app.delete("/donations/{donation_id}")
def delete_donation(donation_id: int):
    with get_connection() as conn:
        # CHANGED: same RETURNING trick, so delete + 404 check is one query.
        row = conn.execute(
            "DELETE FROM donations WHERE id = %s RETURNING *", (donation_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Donation not found")
        return {"message": f"Donation with ID {donation_id} has been deleted.", "deleted_donation": row}

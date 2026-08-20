"""
Database connection setup for Ethara Seat Allocation System.
Uses SQLite for local/demo use (PostgreSQL-compatible via SQLAlchemy ORM,
so switching DATABASE_URL to a Postgres connection string is a drop-in change).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ethara_seats.db")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
else:
    # Postgres over a network (e.g. Railway's proxy) can silently drop an
    # idle or long-lived connection without the client noticing — the next
    # query then hangs waiting on a dead socket until the OS-level TCP
    # timeout finally kicks in (which can be minutes). Two settings fix this:
    #   - pool_pre_ping: SQLAlchemy quietly checks the connection is alive
    #     (a fast SELECT 1) before handing it out, and transparently opens a
    #     fresh one if it's dead, instead of hanging on the caller's query.
    #   - pool_recycle: proactively recycles connections older than this many
    #     seconds, so we never rely on a connection that's lived long enough
    #     to be at risk of a proxy timing it out from the other end.
    #   - connect_timeout / keepalives: fail fast (~10s) if a *new* connection
    #     attempt itself can't reach the server, and keep idle connections
    #     alive at the TCP level so proxies are less likely to kill them.
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        # If a query somehow does hang despite the above, fail after 60s with
        # a clear error instead of sitting there indefinitely.
        "options": "-c statement_timeout=60000",
    }
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=280,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
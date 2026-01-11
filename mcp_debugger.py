from fastmcp import FastMCP
import sqlite3
import json
import os

from pathlib import Path

# Create the MCP server
mcp = FastMCP("MCP Database Debugger")

# Use absolute path relative to this script
DB_PATH = Path(__file__).parent / "mcp.db"

def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def get_database_stats() -> dict:
    """Get counts of events and alerts in the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        total_events = cursor.execute("SELECT count(*) FROM mcp_auth_events").fetchone()[0]
        total_alerts = cursor.execute("SELECT count(*) FROM mcp_alerts").fetchone()[0]
        open_alerts = cursor.execute("SELECT count(*) FROM mcp_alerts WHERE status='open'").fetchone()[0]
        return {
            "total_events": total_events,
            "total_alerts": total_alerts,
            "open_alerts": open_alerts
        }
    finally:
        conn.close()

@mcp.tool()
def get_recent_events(limit: int = 5) -> str:
    """Get the most recent authentication events."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM mcp_auth_events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        # Convert rows to dicts and handle datetime serialization via str default
        return json.dumps([dict(row) for row in rows], default=str, indent=2)
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run(show_banner=False)

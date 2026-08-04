"""SQLite storage engine.

Provides SQLite persistence for Phase 0 telemetry trace logging, as well as
tables for Phase 1 codebase chunks and symbol metadata.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any
from models.base import ModelResponse
from core.config import settings


class SQLiteStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or settings.SQLITE_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database schemas for telemetry and code indexing."""
        with self._get_connection() as conn:
            # Phase 0: Telemetry Traces
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    task_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    success INTEGER NOT NULL,
                    metadata TEXT
                )
            """)

            # Phase 1: Code Chunks
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_chunks (
                    id TEXT PRIMARY KEY,
                    repo_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    token_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Phase 1: AST Symbols
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    symbol_name TEXT NOT NULL,
                    symbol_type TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    signature TEXT
                )
            """)
            conn.commit()

    def log_telemetry(
        self,
        task_id: str,
        task_type: str,
        response: ModelResponse,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an execution trace into the telemetry table."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO telemetry_traces 
                (task_id, task_type, model_name, latency_ms, input_tokens, output_tokens, cost_usd, success, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task_type,
                    response.model_name,
                    response.latency_ms,
                    response.input_tokens,
                    response.output_tokens,
                    response.cost_usd,
                    1 if success else 0,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

    def get_telemetry_summary(self) -> dict[str, Any]:
        """Aggregate performance metrics across logged executions."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    AVG(latency_ms) as avg_latency,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cost_usd) as total_cost,
                    SUM(success) as successful_calls
                FROM telemetry_traces
            """)
            row = cursor.fetchone()
            if not row or row["total_calls"] == 0:
                return {"total_calls": 0, "avg_latency_ms": 0.0, "total_cost_usd": 0.0}

            return {
                "total_calls": row["total_calls"],
                "avg_latency_ms": round(row["avg_latency"] or 0.0, 2),
                "total_input_tokens": row["total_input_tokens"] or 0,
                "total_output_tokens": row["total_output_tokens"] or 0,
                "total_cost_usd": round(row["total_cost"] or 0.0, 6),
                "success_rate": round((row["successful_calls"] / row["total_calls"]) * 100.0, 2),
            }
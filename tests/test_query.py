"""Contract tests for reportdb.query.

Every test calls at least one real stub, so the initial implementation is
expected to fail all 15 tests with NotImplementedError.
"""

from __future__ import annotations

import sqlite3

import pytest

from reportdb.query import (
    InvalidQuery,
    build_search,
    build_select,
    check_identifier,
    escape_like,
    quote_ident,
)

SEARCH_ALLOWED = {"tables": ["notes"], "columns": ["value"]}


def _run_notes_query(sql: str, params: list, values: list[str]) -> list[tuple]:
    """Create a fresh in-memory notes table and execute the generated query."""
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE notes (value TEXT NOT NULL)")
        conn.executemany(
            "INSERT INTO notes (value) VALUES (?)",
            [(value,) for value in values],
        )
        return sorted(conn.execute(sql, params).fetchall())


def test_rejects_semicolon_identifier() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users; DROP TABLE users", ["id"], [], 10, {})
    with pytest.raises(InvalidQuery):
        quote_ident("users; DROP TABLE users")


def test_rejects_sql_comment_identifier() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users", ["name--"], [], 10, {})


def test_rejects_invalid_table_identifier() -> None:
    with pytest.raises(InvalidQuery):
        build_select("bad table", ["id"], [], 10, {})


def test_rejects_order_column_not_in_allowlist() -> None:
    # Callers must validate ORDER BY fields with the same exact whitelist used
    # for table and column names.
    with pytest.raises(InvalidQuery):
        check_identifier("created_at", {"id", "name"})


def test_rejects_invalid_order_direction() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users", ["id"], [("name", "DESC; --")], 10, {})


def test_rejects_subquery_in_order_by() -> None:
    with pytest.raises(InvalidQuery):
        build_select(
            "users",
            ["id"],
            [("(SELECT secret FROM users LIMIT 1)", "ASC")],
            10,
            {},
        )


def test_percent_wildcard_is_escaped() -> None:
    assert escape_like("50%") == "50\\%"
    sql, params = build_search("notes", "value", "50%", 100, SEARCH_ALLOWED)
    assert sql == (
        'SELECT "value" FROM "notes" '
        "WHERE \"value\" LIKE ? ESCAPE '\\' LIMIT ?"
    )
    assert params == ["%50\\%%", 100]
    rows = _run_notes_query(
        sql,
        params,
        ["50% off", "50X off", "500 off"],
    )
    assert rows == [("50% off",)]


def test_underscore_wildcard_is_escaped() -> None:
    assert escape_like("a_b") == "a\\_b"
    sql, params = build_search("notes", "value", "a_b", 100, SEARCH_ALLOWED)
    assert params == ["%a\\_b%", 100]
    rows = _run_notes_query(
        sql,
        params,
        ["a_b", "axb", "a_b_c"],
    )
    assert rows == [("a_b",), ("a_b_c",)]


def test_like_escape_character_is_escaped() -> None:
    assert escape_like("a\\b") == "a\\\\b"
    sql, params = build_search("notes", "value", "a\\b", 100, SEARCH_ALLOWED)
    assert params == ["%a\\\\b%", 100]
    rows = _run_notes_query(
        sql,
        params,
        ["a\\b", "axb", "a_b"],
    )
    assert rows == [("a\\b",)]


def test_rejects_negative_limit() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users", ["id"], [], -1, {})


def test_rejects_limit_above_maximum() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users", ["id"], [], 1001, {})


def test_rejects_non_integer_limit() -> None:
    with pytest.raises(InvalidQuery):
        build_select("users", ["id"], [], "1; --", {})  # type: ignore[arg-type]


def test_whitelist_match_is_case_insensitive() -> None:
    assert check_identifier("USERS", {"users", "audit_log"}) == "users"


def test_whitelist_rejects_prefix_lookalike() -> None:
    with pytest.raises(InvalidQuery):
        check_identifier("users_old", {"users"})


def test_normal_select_executes_in_memory_database() -> None:
    sql, params = build_select(
        "users",
        ["id", "name"],
        [("name", "ASC")],
        10,
        {"role": "admin", "id": [1, 3]},
    )
    assert sql == (
        'SELECT "id", "name" FROM "users" '
        'WHERE "role" = ? AND "id" IN (?, ?) '
        'ORDER BY "name" ASC LIMIT ?'
    )
    assert params == ["admin", 1, 3, 10]
    assert sql.count("?") == len(params) == 4
    assert "admin" not in sql
    assert "1; --" not in sql

    with sqlite3.connect(":memory:") as conn:
        conn.execute(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "role TEXT NOT NULL"
            ")"
        )
        conn.executemany(
            "INSERT INTO users (id, name, role) VALUES (?, ?, ?)",
            [
                (1, "alice", "admin"),
                (2, "bob", "user"),
                (3, "carol", "admin"),
                (4, "dave", "admin' OR 1=1 --"),
            ],
        )
        rows = conn.execute(sql, params).fetchall()

    assert rows == [(1, "alice"), (3, "carol")]

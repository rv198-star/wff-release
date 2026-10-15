"""Mechanically inventory actual SQLite DDL without executing business writes.

Only table declarations, indexes (including partial indexes) and rejecting BEFORE
triggers are admitted. Predicates are retained in full, not evaluated as truth.
Every complete definition is itself a registered contract fact: parsing columns
cannot hide an added CHECK, default, key, trigger or unknown enum restriction.
"""
import re
import sqlite3
from common.p3_gap_records import GapDecisionError


def _statements(text):
    # sqlite3.complete_statement handles quoted semicolons and trigger bodies.
    pending = ""
    for char in text:
        pending += char
        if char == ";" and sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if _strip_comments(pending).strip():
        raise GapDecisionError("Incomplete SQLite DDL statement")


def _strip_comments(text):
    result = []; i = 0; quote = None
    while i < len(text):
        c = text[i]
        if quote:
            result.append(c)
            if c == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    result.append(text[i + 1]); i += 1
                else: quote = None
            i += 1; continue
        if c in ("'", '"', '`'):
            quote = c; result.append(c); i += 1; continue
        if text[i:i+2] == '--':
            j = text.find('\n', i + 2); i = len(text) if j < 0 else j
            result.append(' '); continue
        if text[i:i+2] == '/*':
            j = text.find('*/', i + 2)
            if j < 0: raise GapDecisionError("Unclosed SQLite comment")
            i = j + 2; result.append(' '); continue
        result.append(c); i += 1
    if quote: raise GapDecisionError("Unclosed SQLite quoted token")
    return ''.join(result)


def sqlite_facts(text):
    """A strict SQLite subset; unsupported statements remain evidence gaps."""
    result = []; tables = []; definitions = []; keys = set()
    ident = r'(?:[A-Za-z_][A-Za-z_0-9]*|"[A-Za-z_][A-Za-z_0-9]*")'
    for raw in _statements(text):
        sql = _strip_comments(raw).strip()
        if not sql: continue
        if re.fullmatch(r'PRAGMA\s+foreign_keys\s*=\s*(?:ON|1)\s*;', sql, re.I):
            definitions.append(sql); continue
        if re.fullmatch(r'PRAGMA\s+recursive_triggers\s*=\s*(?:ON|1)\s*;', sql, re.I):
            result.append({'id':'db:pragma:recursive_triggers:definition','kind':'api_fields','value':sql})
            definitions.append(sql); continue
        table = re.fullmatch(r'CREATE\s+TABLE\s+(' + ident + r')\s*\((.+)\)\s*;', sql, re.I | re.S)
        index = re.fullmatch(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(' + ident + r')\s+ON\s+(' + ident + r')\s*\(\s*' + ident + r'(?:\s+(?:ASC|DESC))?(?:\s*,\s*' + ident + r'(?:\s+(?:ASC|DESC))?)*\s*\)(?:\s+WHERE\s+.+)?\s*;', sql, re.I | re.S)
        rejection = r"RAISE\s*\(\s*ABORT\s*,\s*'(?:[^']|'')*'\s*\)"
        trigger = re.fullmatch(r"CREATE\s+TRIGGER\s+(" + ident + r")\s+BEFORE\s+(?:INSERT|UPDATE|DELETE)\s+ON\s+(" + ident + r")(?:\s+WHEN\s+.+?)?\s+BEGIN\s+SELECT\s+(?:" + rejection + r"|CASE\s+WHEN\s+.+?\s+THEN\s+" + rejection + r"\s+END)\s*;\s*END\s*;", sql, re.I | re.S)
        # No additional SQL statements can hide in a predicate or CASE body.
        # Quoted semicolons in strings/identifiers do not delimit statements.
        unquoted = re.sub(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|`(?:[^`]|``)*`", "Q", sql)
        if unquoted.count(';') != (2 if trigger else 1):
            raise GapDecisionError("Unsupported SQLite statement sequence")
        match = table or index or trigger
        if not match:
            raise GapDecisionError("Unsupported SQLite DDL cannot prove no new facts")
        name = match[1].strip('"'); kind = 'table' if table else 'index' if index else 'trigger'
        key = (kind, name)
        if key in keys: raise GapDecisionError("Duplicate SQLite declaration")
        keys.add(key)
        # Exact lexical definition (apart from comments) includes all constraints.
        result.append({'id': 'db:' + kind + ':' + name + ':definition', 'kind': 'api_fields', 'value': sql})
        if table: tables.append(name)
        definitions.append(sql)
    if not tables: raise GapDecisionError("No actual SQLite table declarations")
    database = sqlite3.connect(':memory:')
    try:
        # No extensions or user functions are installed; no data statements,
        # external databases, arbitrary PRAGMAs, views or CTAS pass the grammar.
        database.enable_load_extension(False)
        for sql in definitions: database.execute(sql)
        for table in tables:
            result.append({'id': 'db:' + table, 'kind': 'entities', 'value': table})
            for row in database.execute('PRAGMA table_xinfo("' + table + '")'):
                _, name, data_type, *_ = row
                if not data_type: raise GapDecisionError("SQLite column type is unspecified")
                result.append({'id': 'db:' + table + '.' + name, 'kind': 'api_fields', 'value': [name, data_type.lower()]})
    except sqlite3.Error as exc:
        raise GapDecisionError("Invalid or unsupported realized SQLite DDL") from exc
    finally: database.close()
    return result

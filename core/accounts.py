"""Contas locais e papeis (Master / User) do aplicativo.

Versao local, antecipada em 23/11/2026 (docs/11, decisao 21): e-mail e senha, dois papeis,
o Master define quem e Master. Fica FORA da base de referencia e das tabelas de parametros:
o arquivo de contas nao entra no git (`local_accounts.sqlite`, ver .gitignore).

Esta camada controla o acesso da INTERFACE. Ela nao protege dados que estejam no repositorio
publico; ver a nota da decisao 2. Para a publicacao, a identidade passa a vir de um login
externo e esta tabela de papeis por e-mail continua valendo.

Nao importa streamlit (regra do `core/`).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time

MASTER = "Master"
USER = "User"
ROLES = (MASTER, USER)

MIN_PASSWORD = 8
PBKDF2_ITERATIONS = 200_000
MAX_FAILURES = 5          # tentativas erradas seguidas antes do bloqueio
LOCK_SECONDS = 300        # duracao do bloqueio

DDL = """
CREATE TABLE IF NOT EXISTS Account (
    Email        TEXT PRIMARY KEY,
    PasswordHash TEXT NOT NULL,
    Salt         TEXT NOT NULL,
    Iterations   INTEGER NOT NULL,
    Role         TEXT NOT NULL CHECK (Role IN ('Master','User')),
    Failures     INTEGER NOT NULL DEFAULT 0,
    LockedUntil  REAL NOT NULL DEFAULT 0,
    CreatedAt    REAL NOT NULL
)
"""

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccountError(ValueError):
    """Erro de regra de negocio, com mensagem para o usuario."""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(DDL)
    conn.commit()
    return conn


def normalize_email(email: str | None) -> str:
    e = (email or "").strip().lower()
    if not _EMAIL.match(e):
        raise AccountError("Enter a valid e-mail address.")
    return e


def _check_password(password: str | None) -> str:
    if not password or len(password) < MIN_PASSWORD:
        raise AccountError(f"The password needs at least {MIN_PASSWORD} characters.")
    return password


def _hash(password: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()


def has_accounts(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM Account").fetchone()[0] > 0


def count_masters(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM Account WHERE Role=?", (MASTER,)).fetchone()[0]


def role_of(conn: sqlite3.Connection, email: str) -> str | None:
    row = conn.execute("SELECT Role FROM Account WHERE Email=?",
                       (email.strip().lower(),)).fetchone()
    return row["Role"] if row else None


def _insert(conn: sqlite3.Connection, email: str, password: str, role: str,
            now: float) -> None:
    salt = secrets.token_bytes(16)
    conn.execute(
        "INSERT INTO Account (Email, PasswordHash, Salt, Iterations, Role, CreatedAt) "
        "VALUES (?,?,?,?,?,?)",
        (email, _hash(password, salt, PBKDF2_ITERATIONS), salt.hex(), PBKDF2_ITERATIONS,
         role, now))
    conn.commit()


def create_account(conn: sqlite3.Connection, email: str, password: str, *,
                   now: float | None = None) -> str:
    """Conta nova, sempre com o papel User. Retorna o e-mail normalizado."""
    e = normalize_email(email)
    _check_password(password)
    if role_of(conn, e):
        raise AccountError("This e-mail already has an account.")
    _insert(conn, e, password, USER, time.time() if now is None else now)
    return e


def bootstrap_master(conn: sqlite3.Connection, email: str, password: str,
                     installation_secret: str | None, candidate_secret: str | None, *,
                     now: float | None = None) -> str:
    """Cria o primeiro Master. So vale se nao ha Master e se a senha de instalacao
    (variavel `I3ET_MASTER_PASSWORD` ou segredo `master_password`) foi informada."""
    if count_masters(conn):
        raise AccountError("A master account already exists.")
    if not installation_secret:
        raise AccountError("No installation master password is configured.")
    if not candidate_secret or not hmac.compare_digest(
            candidate_secret.encode("utf-8"), installation_secret.encode("utf-8")):
        raise AccountError("Wrong installation master password.")
    e = normalize_email(email)
    _check_password(password)
    t = time.time() if now is None else now
    if role_of(conn, e):                               # conta de User existente: promove
        conn.execute("UPDATE Account SET Role=? WHERE Email=?", (MASTER, e))
        conn.commit()
        change_password(conn, e, password)
    else:
        _insert(conn, e, password, MASTER, t)
    return e


def authenticate(conn: sqlite3.Connection, email: str, password: str, *,
                 now: float | None = None) -> str:
    """Retorna o papel se e-mail e senha conferem. Bloqueia depois de MAX_FAILURES erros
    seguidos por LOCK_SECONDS. A mensagem nao diz se o e-mail existe."""
    t = time.time() if now is None else now
    e = (email or "").strip().lower()
    row = conn.execute("SELECT * FROM Account WHERE Email=?", (e,)).fetchone()
    if row is None:
        raise AccountError("Wrong e-mail or password.")
    if row["LockedUntil"] > t:
        minutos = max(1, int((row["LockedUntil"] - t) // 60) + 1)
        raise AccountError(f"Too many attempts. Try again in about {minutos} min.")
    esperado = row["PasswordHash"]
    obtido = _hash(password or "", bytes.fromhex(row["Salt"]), row["Iterations"])
    if hmac.compare_digest(esperado, obtido):
        conn.execute("UPDATE Account SET Failures=0, LockedUntil=0 WHERE Email=?", (e,))
        conn.commit()
        return row["Role"]
    falhas = row["Failures"] + 1
    trava = t + LOCK_SECONDS if falhas >= MAX_FAILURES else 0
    conn.execute("UPDATE Account SET Failures=?, LockedUntil=? WHERE Email=?",
                 (0 if trava else falhas, trava, e))
    conn.commit()
    raise AccountError("Wrong e-mail or password.")


def change_password(conn: sqlite3.Connection, email: str, new_password: str) -> None:
    e = normalize_email(email)
    _check_password(new_password)
    if not role_of(conn, e):
        raise AccountError("Account not found.")
    salt = secrets.token_bytes(16)
    conn.execute("UPDATE Account SET PasswordHash=?, Salt=?, Iterations=?, Failures=0, "
                 "LockedUntil=0 WHERE Email=?",
                 (_hash(new_password, salt, PBKDF2_ITERATIONS), salt.hex(),
                  PBKDF2_ITERATIONS, e))
    conn.commit()


def list_accounts(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT Email, Role, CreatedAt FROM Account ORDER BY Role DESC, Email")]


def _require_master(conn: sqlite3.Connection, actor: str) -> None:
    if role_of(conn, actor) != MASTER:
        raise AccountError("Only a master user can change roles.")


def set_role(conn: sqlite3.Connection, actor: str, target: str, role: str) -> None:
    """O Master promove ou rebaixa. O ultimo Master nao pode ser rebaixado."""
    _require_master(conn, actor)
    if role not in ROLES:
        raise AccountError("Unknown role.")
    t = target.strip().lower()
    atual = role_of(conn, t)
    if not atual:
        raise AccountError("Account not found.")
    if atual == role:
        return
    if atual == MASTER and role == USER and count_masters(conn) <= 1:
        raise AccountError("The last master cannot be demoted. Promote another user first "
                           "or use transfer.")
    conn.execute("UPDATE Account SET Role=? WHERE Email=?", (role, t))
    conn.commit()


def transfer_master(conn: sqlite3.Connection, actor: str, target: str) -> None:
    """O Master atual passa o papel a outro usuario e vira User, em uma unica gravacao."""
    _require_master(conn, actor)
    a, t = actor.strip().lower(), target.strip().lower()
    if a == t:
        raise AccountError("Choose another account.")
    if not role_of(conn, t):
        raise AccountError("Account not found.")
    conn.execute("UPDATE Account SET Role=? WHERE Email=?", (MASTER, t))
    conn.execute("UPDATE Account SET Role=? WHERE Email=?", (USER, a))
    conn.commit()

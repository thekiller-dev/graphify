"""Identity, tenancy and API keys — stdlib only (sqlite3 + hashlib + secrets).

Deliberately small and auditable: this is the security boundary of the hosted
product, so there is no ORM, no migration framework and no third-party auth
dependency to trust. Passwords are PBKDF2-HMAC-SHA256 with a per-user salt;
session tokens and API keys are stored **hashed** (a DB leak does not leak
credentials) and compared through their digest.

Multi-tenancy model:

    user ──< member >── workspace ──< api_key
                            │
                            └── graph_path (one graph.json per workspace)

A request is authorised by a session cookie (browser) or an API key (IDE /
agent); either way it resolves to exactly one workspace, and every read
endpoint is scoped to it.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

PBKDF2_ROUNDS = 210_000
SESSION_TTL = 60 * 60 * 24 * 30  # 30 days
SESSION_COOKIE = "gf_session"
KEY_PREFIX = "gf_"
ROLES = ("owner", "member", "viewer")

_SLUG = re.compile(r"[^a-z0-9]+")


def _now() -> int:
    return int(time.time())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def slugify(name: str, fallback: str = "workspace") -> str:
    slug = _SLUG.sub("-", (name or "").lower()).strip("-")[:40]
    return slug or fallback


# ------------------------------------------------------------------- plans
#
# Plans are data, not code paths: limits live here so changing a plan is a
# config edit, and the enforcement points (create workspace, upload, invite
# accept, every metered request) all read the same table.

PLANS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_month": 0,
        "max_workspaces": 3,
        "max_members": 3,
        "max_nodes": 250_000,
        "max_api_calls_month": 50_000,
        "max_upload_mb": 100,
        "blurb": "Local graphs, community support. AST extraction stays free forever.",
    },
    "pro": {
        "name": "Pro",
        "price_month": 49,
        "max_workspaces": 50,
        "max_members": 25,
        "max_nodes": 5_000_000,
        "max_api_calls_month": 2_000_000,
        "max_upload_mb": 1000,
        "blurb": "Big corpora, teams, priority extraction queue.",
    },
}
DEFAULT_PLAN = "free"


def plan_of(plan_id: str | None) -> dict:
    return PLANS.get(plan_id or DEFAULT_PLAN, PLANS[DEFAULT_PLAN])


def period_now() -> str:
    return time.strftime("%Y-%m")


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.message = message
        self.status = status


class LimitExceeded(AuthError):
    """A plan limit was hit. 402, not 403: the credential is fine, the plan isn't."""

    def __init__(self, message: str):
        super().__init__(message, 402)


@dataclass
class User:
    id: str
    email: str
    name: str
    created_at: int

    @property
    def display(self) -> str:
        return self.name or self.email.split("@")[0]


@dataclass
class Workspace:
    id: str
    slug: str
    name: str
    graph_path: str
    owner_id: str
    role: str = "owner"
    created_at: int = 0
    plan: str = DEFAULT_PLAN

    @property
    def graph_exists(self) -> bool:
        return Path(self.graph_path).exists()


@dataclass
class ApiKey:
    id: str
    workspace_id: str
    name: str
    prefix: str
    created_at: int
    last_used_at: int | None
    revoked_at: int | None = None



class Auth:
    """SQLite-backed identity store. One connection per call, guarded by a lock:
    sqlite handles the concurrency and we never hold a cursor across an await."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(
            db_path or os.environ.get("GRAPHIFY_APP_DB") or Path("saas") / "data" / "app.db"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._migrate()

    # ------------------------------------------------------------------- db

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _migrate(self) -> None:
        with self._lock, self._connect() as c:
            c.executescript(
                """
CREATE TABLE IF NOT EXISTS users (
  id         TEXT PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL DEFAULT '',
  pw_hash    TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS workspaces (
  id         TEXT PRIMARY KEY,
  slug       TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  graph_path TEXT NOT NULL,
  owner_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role         TEXT NOT NULL DEFAULT 'member',
  created_at   INTEGER NOT NULL,
  PRIMARY KEY (workspace_id, user_id)
);
CREATE TABLE IF NOT EXISTS api_keys (
  id           TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL DEFAULT 'default',
  prefix       TEXT NOT NULL,
  key_hash     TEXT NOT NULL UNIQUE,
  created_at   INTEGER NOT NULL,
  last_used_at INTEGER,
  revoked_at   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_members_user ON members(user_id);
CREATE INDEX IF NOT EXISTS idx_keys_ws ON api_keys(workspace_id);
CREATE TABLE IF NOT EXISTS usage (
  workspace_id   TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  period         TEXT NOT NULL,
  api_calls      INTEGER NOT NULL DEFAULT 0,
  mcp_calls      INTEGER NOT NULL DEFAULT 0,
  uploads        INTEGER NOT NULL DEFAULT 0,
  uploaded_bytes INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (workspace_id, period)
);
CREATE TABLE IF NOT EXISTS invites (
  id           TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email        TEXT NOT NULL,
  role         TEXT NOT NULL DEFAULT 'member',
  token        TEXT NOT NULL UNIQUE,
  created_by   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at   INTEGER NOT NULL,
  expires_at   INTEGER NOT NULL,
  accepted_at  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_invites_ws ON invites(workspace_id);
"""
            )
            # Added after the first release: workspaces carry their own plan so
            # each tenant is billed (and limited) independently.
            cols = {r["name"] for r in c.execute("PRAGMA table_info(workspaces)")}
            if "plan" not in cols:
                c.execute(
                    "ALTER TABLE workspaces ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'"
                )

    # ---------------------------------------------------------------- users

    def signup(self, email: str, password: str, name: str = "") -> tuple[User, str]:
        email = (email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise AuthError("a valid email is required", 400)
        if len(password or "") < 8:
            raise AuthError("password must be at least 8 characters", 400)
        uid = uuid.uuid4().hex
        with self._lock, self._connect() as c:
            if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise AuthError("that email is already registered", 409)
            c.execute(
                "INSERT INTO users (id,email,name,pw_hash,created_at) VALUES (?,?,?,?,?)",
                (uid, email, (name or "").strip(), hash_password(password), _now()),
            )
        return User(uid, email, (name or "").strip(), _now()), self.create_session(uid)

    def login(self, email: str, password: str) -> tuple[User, str]:
        email = (email or "").strip().lower()
        with self._lock, self._connect() as c:
            row = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        # Verify even when the user is missing is impossible, so fail fast —
        # but keep the message identical to a wrong password (no user enum).
        if not row or not verify_password(password or "", row["pw_hash"]):
            raise AuthError("invalid email or password", 401)
        return self._user(row), self.create_session(row["id"])

    def logout(self, token: str) -> None:
        if not token:
            return
        with self._lock, self._connect() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_digest(token),))

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT INTO sessions (token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
                (_digest(token), user_id, _now(), _now() + SESSION_TTL),
            )
            c.execute("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
        return token

    def user_from_token(self, token: str | None) -> User | None:
        if not token:
            return None
        with self._lock, self._connect() as c:
            row = c.execute(
                """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token_hash=? AND s.expires_at > ?""",
                (_digest(token), _now()),
            ).fetchone()
        return self._user(row) if row else None

    @staticmethod
    def _user(row: sqlite3.Row) -> User:
        return User(row["id"], row["email"], row["name"], row["created_at"])

    def user_count(self) -> int:
        with self._lock, self._connect() as c:
            return int(c.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    # ----------------------------------------------------------- workspaces

    def create_workspace(
        self, owner_id: str, name: str, graph_path: str, slug: str | None = None
    ) -> Workspace:
        slug = slugify(slug or name)
        ws_id = uuid.uuid4().hex[:16]
        with self._lock, self._connect() as c:
            if c.execute("SELECT 1 FROM workspaces WHERE slug=?", (slug,)).fetchone():
                slug = f"{slug}-{ws_id[:5]}"
            c.execute(
                "INSERT INTO workspaces (id,slug,name,graph_path,owner_id,created_at) VALUES (?,?,?,?,?,?)",
                (ws_id, slug, name.strip(), str(graph_path), owner_id, _now()),
            )
            c.execute(
                "INSERT INTO members (workspace_id,user_id,role,created_at) VALUES (?,?,?,?)",
                (ws_id, owner_id, "owner", _now()),
            )
            row = c.execute("SELECT * FROM workspaces WHERE id=?", (ws_id,)).fetchone()
        return Workspace(row["id"], row["slug"], row["name"], row["graph_path"], row["owner_id"], "owner", row["created_at"], row["plan"])

    def workspaces_for(self, user_id: str) -> list[Workspace]:
        with self._lock, self._connect() as c:
            rows = c.execute(
                """SELECT w.*, m.role FROM members m JOIN workspaces w ON w.id = m.workspace_id
                   WHERE m.user_id=? ORDER BY w.created_at""",
                (user_id,),
            ).fetchall()
        return [
            Workspace(r["id"], r["slug"], r["name"], r["graph_path"], r["owner_id"], r["role"], r["created_at"], r["plan"])
            for r in rows
        ]

    def workspace(self, ws_id: str) -> Workspace | None:
        with self._lock, self._connect() as c:
            row = c.execute(
                "SELECT * FROM workspaces WHERE id=? OR slug=?", (ws_id, ws_id)
            ).fetchone()
        if not row:
            return None
        return Workspace(row["id"], row["slug"], row["name"], row["graph_path"], row["owner_id"], "owner", row["created_at"], row["plan"])

    def role_of(self, ws_id: str, user_id: str) -> str | None:
        with self._lock, self._connect() as c:
            row = c.execute(
                "SELECT role FROM members WHERE workspace_id=? AND user_id=?", (ws_id, user_id)
            ).fetchone()
        return row["role"] if row else None

    def find_by_slug(self, slug: str) -> Workspace | None:
        with self._lock, self._connect() as c:
            row = c.execute("SELECT * FROM workspaces WHERE slug=?", (slug,)).fetchone()
        if not row:
            return None
        return Workspace(row["id"], row["slug"], row["name"], row["graph_path"], row["owner_id"], "owner", row["created_at"], row["plan"])

    # ------------------------------------------------------------- api keys

    def create_api_key(self, ws_id: str, user_id: str, name: str = "default") -> tuple[ApiKey, str]:
        raw = KEY_PREFIX + secrets.token_urlsafe(27)
        key_id = uuid.uuid4().hex[:16]
        prefix = raw[: len(KEY_PREFIX) + 6]
        with self._lock, self._connect() as c:
            c.execute(
                """INSERT INTO api_keys (id,workspace_id,user_id,name,prefix,key_hash,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (key_id, ws_id, user_id, name.strip() or "default", prefix, _digest(raw), _now()),
            )
        return ApiKey(key_id, ws_id, name.strip() or "default", prefix, _now(), None), raw

    def api_keys(self, ws_id: str) -> list[ApiKey]:
        with self._lock, self._connect() as c:
            rows = c.execute(
                "SELECT * FROM api_keys WHERE workspace_id=? ORDER BY created_at DESC", (ws_id,)
            ).fetchall()
        return [
            ApiKey(r["id"], r["workspace_id"], r["name"], r["prefix"], r["created_at"], r["last_used_at"], r["revoked_at"])
            for r in rows
        ]

    def revoke_api_key(self, key_id: str, ws_id: str) -> bool:
        with self._lock, self._connect() as c:
            cur = c.execute(
                "UPDATE api_keys SET revoked_at=? WHERE id=? AND workspace_id=? AND revoked_at IS NULL",
                (_now(), key_id, ws_id),
            )
        return cur.rowcount > 0

    def workspace_from_key(self, raw: str) -> tuple[Workspace, ApiKey] | None:
        """Resolve a bearer key to its workspace. Lookup is by digest, so the
        plaintext key is never stored and never compared in Python."""
        if not raw or not raw.startswith(KEY_PREFIX):
            return None
        with self._lock, self._connect() as c:
            row = c.execute(
                """SELECT k.*, w.id AS ws_id, w.slug, w.name, w.graph_path, w.owner_id, w.created_at AS ws_created
                   FROM api_keys k JOIN workspaces w ON w.id = k.workspace_id
                   WHERE k.key_hash=? AND k.revoked_at IS NULL""",
                (_digest(raw),),
            ).fetchone()
            if not row:
                return None
            c.execute(
                "UPDATE api_keys SET last_used_at=? WHERE id=?", (_now(), row["id"])
            )
        ws = Workspace(row["ws_id"], row["slug"], row["name"], row["graph_path"], row["owner_id"], "owner", row["ws_created"], row["plan"] if "plan" in row.keys() else DEFAULT_PLAN)
        key = ApiKey(row["id"], row["workspace_id"], row["name"], row["prefix"], row["created_at"], row["last_used_at"], row["revoked_at"])
        return ws, key


    # ---------------------------------------------------------- plans & usage

    def set_plan(self, ws_id: str, plan_id: str) -> Workspace | None:
        if plan_id not in PLANS:
            raise AuthError(f"unknown plan: {plan_id}", 400)
        with self._lock, self._connect() as c:
            c.execute("UPDATE workspaces SET plan=? WHERE id=?", (plan_id, ws_id))
        return self.workspace(ws_id)

    def meter(self, ws_id: str, kind: str, n: int = 1, bytes_: int = 0) -> None:
        col = {"api": "api_calls", "mcp": "mcp_calls", "upload": "uploads"}.get(kind)
        if not col:
            return
        period = period_now()
        with self._lock, self._connect() as c:
            c.execute(
                f"""INSERT INTO usage (workspace_id,period,{col},uploaded_bytes)
                    VALUES (?,?,?,?)
                    ON CONFLICT(workspace_id,period) DO UPDATE SET
                      {col}={col}+excluded.{col},
                      uploaded_bytes=uploaded_bytes+excluded.uploaded_bytes""",
                (ws_id, period, n, bytes_ if kind == "upload" else 0),
            )

    def usage(self, ws_id: str, period: str | None = None) -> dict:
        period = period or period_now()
        with self._lock, self._connect() as c:
            row = c.execute(
                "SELECT * FROM usage WHERE workspace_id=? AND period=?", (ws_id, period)
            ).fetchone()
        if not row:
            return {"period": period, "api_calls": 0, "mcp_calls": 0, "uploads": 0, "uploaded_bytes": 0}
        return {
            "period": period,
            "api_calls": row["api_calls"],
            "mcp_calls": row["mcp_calls"],
            "uploads": row["uploads"],
            "uploaded_bytes": row["uploaded_bytes"],
        }

    def usage_history(self, ws_id: str) -> list[dict]:
        with self._lock, self._connect() as c:
            rows = c.execute(
                "SELECT * FROM usage WHERE workspace_id=? ORDER BY period DESC LIMIT 12",
                (ws_id,),
            ).fetchall()
        return [
            {"period": r["period"], "api_calls": r["api_calls"], "mcp_calls": r["mcp_calls"],
             "uploads": r["uploads"], "uploaded_bytes": r["uploaded_bytes"]}
            for r in rows
        ]

    def check_api_quota(self, ws: Workspace) -> None:
        limit = plan_of(ws.plan)["max_api_calls_month"]
        used = self.usage(ws.id)["api_calls"]
        if used >= limit:
            raise LimitExceeded(
                f"monthly API quota exhausted ({used}/{limit} on plan "
                f"'{plan_of(ws.plan)['name']}'). Upgrade under Billing."
            )

    # ---------------------------------------------------------------- members

    def members(self, ws_id: str) -> list[dict]:
        with self._lock, self._connect() as c:
            rows = c.execute(
                """SELECT u.id, u.email, u.name, m.role, m.created_at
                   FROM members m JOIN users u ON u.id = m.user_id
                   WHERE m.workspace_id=? ORDER BY m.created_at""",
                (ws_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def remove_member(self, ws_id: str, user_id: str) -> bool:
        with self._lock, self._connect() as c:
            if c.execute(
                "SELECT 1 FROM members WHERE workspace_id=? AND user_id=? AND role='owner'",
                (ws_id, user_id),
            ).fetchone():
                raise AuthError("the owner cannot be removed", 400)
            cur = c.execute(
                "DELETE FROM members WHERE workspace_id=? AND user_id=?", (ws_id, user_id)
            )
        return cur.rowcount > 0

    # ---------------------------------------------------------------- invites

    def create_invite(self, ws_id: str, email: str, role: str, by_user: str) -> tuple[str, dict]:
        email = (email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise AuthError("a valid email is required", 400)
        if role not in ("member", "viewer"):
            raise AuthError("role must be member or viewer", 400)
        if any(m["email"] == email for m in self.members(ws_id)):
            raise AuthError("that person is already a member", 409)
        token = secrets.token_urlsafe(24)
        inv_id = uuid.uuid4().hex[:16]
        with self._lock, self._connect() as c:
            c.execute(
                """INSERT INTO invites (id,workspace_id,email,role,token,created_by,created_at,expires_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (inv_id, ws_id, email, role, token, by_user, _now(), _now() + 7 * 86400),
            )
        return token, {"id": inv_id, "email": email, "role": role}

    def invites(self, ws_id: str) -> list[dict]:
        with self._lock, self._connect() as c:
            rows = c.execute(
                "SELECT id,email,role,created_at,expires_at,accepted_at FROM invites WHERE workspace_id=? ORDER BY created_at DESC",
                (ws_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def revoke_invite(self, invite_id: str, ws_id: str) -> bool:
        with self._lock, self._connect() as c:
            cur = c.execute(
                "DELETE FROM invites WHERE id=? AND workspace_id=? AND accepted_at IS NULL",
                (invite_id, ws_id),
            )
        return cur.rowcount > 0

    def invite_by_token(self, token: str) -> dict | None:
        with self._lock, self._connect() as c:
            row = c.execute(
                """SELECT i.*, w.name AS ws_name, w.slug FROM invites i
                   JOIN workspaces w ON w.id = i.workspace_id WHERE i.token=?""",
                (token,),
            ).fetchone()
        if not row or row["accepted_at"] or row["expires_at"] < _now():
            return None
        return {"id": row["id"], "email": row["email"], "role": row["role"],
                "workspace_id": row["workspace_id"], "workspace": row["ws_name"],
                "slug": row["slug"], "expires_at": row["expires_at"]}

    def accept_invite(self, token: str, user: User) -> Workspace | None:
        inv = self.invite_by_token(token)
        if inv is None:
            raise AuthError("invite not found, already used, or expired", 404)
        if inv["email"] != user.email:
            raise AuthError(
                f"this invite was sent to {inv['email']}, not {user.email}", 403
            )
        with self._lock, self._connect() as c:
            c.execute(
                "INSERT OR IGNORE INTO members (workspace_id,user_id,role,created_at) VALUES (?,?,?,?)",
                (inv["workspace_id"], user.id, inv["role"], _now()),
            )
            c.execute("UPDATE invites SET accepted_at=? WHERE id=?", (_now(), inv["id"]))
        ws = self.workspace(inv["workspace_id"])
        if ws:
            role = self.role_of(ws.id, user.id) or inv["role"]
            ws.role = role
        return ws


_AUTH: Auth | None = None
_AUTH_LOCK = threading.Lock()


def auth() -> Auth:
    global _AUTH
    with _AUTH_LOCK:
        if _AUTH is None:
            _AUTH = Auth()
        return _AUTH

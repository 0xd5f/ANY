import secrets
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel


class SessionData(BaseModel):
    username: str
    created_at: datetime
    expires_at: datetime


class SessionStorage:

    def __init__(self):
        self.sessions: dict[str, SessionData] = {}

    def set(self, session_id: str, data: SessionData):
        self.sessions[session_id] = data

    def get(self, session_id: str) -> SessionData | None:
        return self.sessions.get(session_id)

    def delete(self, session_id: str):
        self.sessions.pop(session_id, None)


class SessionManager:

    def __init__(self, storage: SessionStorage, expiration_minutes: int = 1440):
        self.storage = storage
        self.expiration = timedelta(minutes=expiration_minutes)

    def set_session(self, username: str) -> str:
        session_id = secrets.token_hex(32)
        session_data = SessionData(username=username, created_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc) + self.expiration)

        self.storage.set(session_id, session_data)

        return session_id

    def get_session(self, session_id: str) -> SessionData | None:
        return self.storage.get(session_id)

    def revoke_session(self, session_id: str):
        self.storage.delete(session_id)

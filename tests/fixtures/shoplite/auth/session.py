import secrets

SESSIONS: dict[str, str] = {}


def create_session(user):
    token = secrets.token_hex(16)
    SESSIONS[token] = user
    return token


def end_session(token):
    SESSIONS.pop(token, None)


def current_user(token):
    return SESSIONS.get(token)

import hashlib


def hash_password(password, salt):
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def check_password(password, salt, stored):
    return hash_password(password, salt) == stored

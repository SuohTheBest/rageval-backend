from passlib.context import CryptContext

from models.User import User
from models.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"])


async def add_user(username, email, plain_password):
    db = SessionLocal()
    hashed_password = pwd_context.hash(plain_password)
    user = User(username=username, email=email, password=hashed_password, avatar="")
    db.add(user)
    db.commit()
    db.close()


async def renew_password(username: str, email: str, plain_password: str):
    db = SessionLocal()
    user = db.query(User).fliter(User.username == username)
    if user is None or user.email != email:
        db.close()
        return False
    hashed_password = pwd_context.hash(plain_password)
    user.password = hashed_password
    db.commit()
    db.close()
    return True


async def get_user_by_credential(credential: str, plain_password: str) -> User | None:
    db = SessionLocal()
    user = (
        db.query(User)
        .filter((User.email == credential) | (User.username == credential))
        .first()
    )
    db.close()
    if user is None:
        return None
    if pwd_context.verify(plain_password, user.password):
        return user
    return None

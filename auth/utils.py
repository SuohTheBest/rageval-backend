from passlib.context import CryptContext

from auth.user_models import User
from database import db

pwd_context = CryptContext(schemes=["bcrypt"])


async def add_user(username, email, plain_password):
    hashed_password = pwd_context.hash(plain_password)
    user = User(username=username, email=email, password=hashed_password, avatar='')
    print(user)
    db.add(user)
    db.commit()


async def get_user_by_email(email: str, plain_password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if pwd_context.verify(plain_password, user.password):
        return user
    return None


async def get_user_by_username(username: str, plain_password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    if pwd_context.verify(plain_password, user.password):
        return user
    return None

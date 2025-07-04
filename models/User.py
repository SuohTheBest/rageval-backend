from sqlalchemy import Column, String, Integer

from models.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True)
    email = Column(String(64), unique=True)
    password = Column(String(255))
    avatar = Column(String(128), default=None)
    role = Column(String(32), default="user") # user, admin

    def __repr__(self):
        return "<User(username='%s', email='%s')>" % (self.username, self.email)

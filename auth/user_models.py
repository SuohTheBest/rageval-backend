from sqlalchemy import Column, Integer, String

from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True)
    email = Column(String(64), unique=True)
    password = Column(String(64))
    avatar = Column(String(128), default=None)

    def __repr__(self):
        return "<User(username='%s', email='%s')>" % (self.username, self.email)

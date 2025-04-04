from sqlalchemy import Column, String, Integer

from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, autoincrement=True)
    username = Column(String(64), primary_key=True, unique=True)
    email = Column(String(64), unique=True)
    password = Column(String(64))
    avatar = Column(String(128), default=None)

    def __repr__(self):
        return "<User(username='%s', email='%s')>" % (self.username, self.email)

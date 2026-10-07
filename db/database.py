from sqlalchemy import create_engine, 
from sqlalchemy.orm import sessionmaker, declarative_base


engine = create_engine("sqlite:///receipts.db", echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

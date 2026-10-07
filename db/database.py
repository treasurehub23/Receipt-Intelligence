from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import psycopg2

engine = create_engine("postgresql://postgres.vswiwxqtuxggnhlqbgjr:[Iam%40tesoro23]@aws-0-eu-west-1.pooler.supabase.com:5432/postgres", echo=True)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
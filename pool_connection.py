from psycopg2 import pool
from contextlib import contextmanager
from dotenv import load_dotenv
import os
load_dotenv()  # loads .env

class DatabasePoolConnection:
    def __init__(self):
        try:
            self.db_pool = pool.SimpleConnectionPool(
                minconn=1,   # Minimum connections in the pool
                maxconn=50,  # Maximum connections in the pool
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST")
            )
            print("Database connection pool created successfully!")
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            self.db_pool = None

    def get_connection(self):
        if self.db_pool:
            return self.db_pool.getconn()
        else:
            raise Exception("Database connection pool is not available.")

    def release_connection(self, conn):
        if self.db_pool and conn:
            self.db_pool.putconn(conn)

    def close_pool(self):
        if self.db_pool:
            self.db_pool.closeall()
            print("Database connection pool closed.")

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.release_connection(conn)




# def __init__(self):
#         try:
#             self.db_pool = pool.SimpleConnectionPool(
#                 minconn=1,  # Minimum connections in the pool
#                 maxconn=50, # Maximum connections in the pool
#                 dbname="fastmealfinder_dev",
#                 user="larry",
#                 password="password",
#                 host="localhost"
#             )
#             print("Database connection pool created successfully!")
#         except Exception as e:
#             print(f"Failed to create connection pool: {e}")
#             self.db_pool = None
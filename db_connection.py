import psycopg2

class DatabaseConnection:
    def connection_setup_dev(self):
        try:
            conn = psycopg2.connect(
                dbname="CHANGED",
                user="CHANGED",
                password="CHANGED",
                host="CHANGED"
            )
            print("Connection successful!")
            return conn
        except Exception as e:
            print(f"Connection failed: {e}")
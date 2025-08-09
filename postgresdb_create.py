import psycopg2
from psycopg2 import sql

conn = psycopg2.connect(
    dbname="postgres",
    user="admin_drunnr",
    password="drunr",
    host="localhost"
)
conn.autocommit = True
cur = conn.cursor()

username = "admin_drunr"
password = "drunr"

# Create user with CREATEDB and LOGIN privileges
cur.execute(
    sql.SQL("CREATE USER {} WITH PASSWORD %s CREATEDB LOGIN").format(sql.Identifier(username)),
    [password]
)

print(f"User {username} created.")
cur.close()
conn.close()
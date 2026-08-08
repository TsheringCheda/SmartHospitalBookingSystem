from werkzeug.security import generate_password_hash
import MySQLdb

db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="YOUR_MYSQL_PASSWORD",
    db="smart_hospital"
)

cur = db.cursor()

# Doctors using 123456
cur.execute("""
UPDATE doctors
SET password=%s
WHERE password='123456'
""", (generate_password_hash("123456"),))

# Doctors using doctor123
cur.execute("""
UPDATE doctors
SET password=%s
WHERE password='doctor123'
""", (generate_password_hash("doctor123"),))

db.commit()

print("✅ All doctor passwords have been hashed successfully.")

cur.close()
db.close()

MYSQL_HOST = "localhost"

MYSQL_USER = "root"

MYSQL_PASSWORD = "Chimivmc777@"

MYSQL_DB = "ehealth_bhutan"

SECRET_KEY = "ehealthbhutan2026"
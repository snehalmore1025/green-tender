import mysql.connector

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root@1234",
        database="greentender"
    )

    cursor = db.cursor(dictionary=True)

    print("✅ Database Connected Successfully!")

except mysql.connector.Error as err:
    print("❌ Database Error:", err)
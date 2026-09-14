import sqlite3


connection = sqlite3.connect("vv.db")
cursor = connection.cursor()


print("REQUIREMENTS")

cursor.execute("SELECT * FROM requirements")

for row in cursor.fetchall():
    print(row)


print("\nTESTS")

cursor.execute("SELECT * FROM tests")

for row in cursor.fetchall():
    print(row)


print("\nDEFECTS")

cursor.execute("SELECT * FROM defects")

for row in cursor.fetchall():
    print(row)


connection.close()
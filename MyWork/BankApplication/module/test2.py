import sqlite3
import os

def startDB():
    global conn
    conn = sqlite3.connect( 'test.db' )
    return conn

def connClose():
    # Commit the changes
    conn.commit()
    # Close the Connection
    conn.close()





# conn.execute('''CREATE TABLE USER_LOGIN
#          (USERID TEXT PRIMARY KEY     NOT NULL,
#          PASSWORD           TEXT    NOT NULL);''')
# print("Table created successfully")


# conn.execute('''CREATE TABLE USER_DATA
#          (USERID TEXT PRIMARY KEY     NOT NULL,
#          NAME           TEXT    NOT NULL,
#          AGE            INT     NOT NULL,
#          ADDRESS        CHAR(50),
#          PHONE         TEXT NOT NULL,
#          ACCCOUNTNO   TEXT NOT NULL);''')
# print("Table created successfully")


# conn.execute('''CREATE TABLE USER_DATA
#          (ACCCOUNTNO   TEXT PRIMARY KEY NOT NULL,
#          BALANCE           INT    NOT NULL);''')
# print("Table created successfully")


#
# conn.execute("INSERT INTO bank_userData (ID,NAME,AGE,ADDRESS,PHONE) \
#       VALUES (1, 'Paul', 32, 'California', 9845991661 )");
#
# conn.execute("INSERT INTO bank_userData (ID,NAME,AGE,ADDRESS,PHONE) \
#       VALUES (2, 'Allen', 25, 'Texas', 9629637192 )");
#
# conn.execute("INSERT INTO bank_userData (ID,NAME,AGE,ADDRESS,PHONE) \
#       VALUES (3, 'Teddy', 23, 'Norway', 8889094591 )");
#
# conn.execute("INSERT INTO bank_userData(ID,NAME,AGE,ADDRESS,PHONE) \
#       VALUES (4, 'Mark', 25, 'Rich-Mond ', 9987654321 )");
#
# conn.commit()





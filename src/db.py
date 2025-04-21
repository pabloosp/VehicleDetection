import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host='localhost',
        user='pablo',
        password='pablo',
        database='vehicle_detection'
    )

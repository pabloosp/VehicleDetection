import os
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host=os.environ['MYSQL_HOST'],
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASS'],
        database=os.environ['MYSQL_DB']
    )

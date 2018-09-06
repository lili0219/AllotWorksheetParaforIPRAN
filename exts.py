import cx_Oracle
import pymysql
import re

def ConnectDB(DB_URL,DBType):
    if not DBType:
        DBType = "Oracle"
    if re.search(r'Ora',DBType,re.I|re.M):
        DBConnect = cx_Oracle.connect(DB_URL)
    elif re.search(r'mysql',DBType,re.I|re.M):
        DBConnect = pymysql.connect(DB_URL)
    else:
        DBConnect = None
    return DBConnect
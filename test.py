import cx_Oracle
DBConnect = cx_Oracle.connect('slview/slview@127.0.0.1:12345/ORCL')
cursorObj = DBConnect.cursor()
statement = "delete from ipranipusedinfo where occupancy='2018012400232' and remark is not null"
cursorObj.parse(statement)
#cursorObj.prepare(statement)
#cursorObj.execute(None,{})
cursorObj.execute(statement)
DBConnect.commit()
print ("*"*10)
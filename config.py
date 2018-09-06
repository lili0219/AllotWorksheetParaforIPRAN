from GetSHDir import GetSHDir
from exts import ConnectDB

DBMap = dict()
#连接数据库
SHDirObj = GetSHDir()
DB_URL   = SHDirObj.dealfilename("DB_Python")
#获取数据库连接串
if not DB_URL:
    raise '数据库URL没有配置，请检查!'
DBType = SHDirObj.dealfilename("DBType")
DBSession = ConnectDB(DB_URL,DBType)
DBMap['DBSession'] = DBSession

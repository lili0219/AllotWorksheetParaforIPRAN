from functools import wraps
from exts import ConnectDB
from config import DB_URL,DBType,DBMap

class ReConnectDB():
    """
    判断数据是否处于连接状态，如果session断开，则重新连接
    """
    def __init__(self,DBMap=None,DB_URL=None,DBType='Oracle'):
        self.DBSession = DBMap.get('DBSession',None)
        self.DB_URL    = DB_URL
        self.DBType    = DBType

    def __call__(self,func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print("wrapper DBSession:",self.DBSession)
            if not self.DBSession:
                DBMap.update({'DBSession':ConnectDB(DB_URL=self.DB_URL ,DBType=self.DBType)})
                #DBMap.update({'DBSession': 'test'})
                return func(*args, **kwargs)
            else:
                return func(*args,**kwargs)
        return wrapper

@ReConnectDB(DBMap=DBMap,DB_URL=DB_URL,DBType=DBType)
def test():
    print("DBSession:{}".format(DBMap['DBSession']))

if __name__ == '__main__':
    test()
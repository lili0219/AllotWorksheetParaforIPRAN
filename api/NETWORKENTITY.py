from flask_restful import Resource
from flask import request
from config import DBMap

class NETWORKENTITY(Resource):
    def __init__(self):
        self.DBSession = DBMap.get('DBSession', None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.BDevID = None
        self.RanIpAddress = None

    def GetCityNode(self):
        """
        根据B设备ID获取地市节点信息
        :return:
        """
        sql = """select c.cityno, c.nodecode, n.nodecode, n.nodefullcode
          from node n, device d, citycodemap c
         where d.nodecode = n.nodecode
           and d.changetype = 0
           and substr(n.nodefullcode,
                      instr(n.nodefullcode,
                            '.',
                            1,
                            (select sy.paravalue
                               from syspara sy
                              where sy.paraname = 'CITYLEVEL')) - 6,
                      6) = c.nodecode
           and d.deviceid = '{BDevID}'""".format(BDevID=self.BDevID)
        self.cursorObj.execute(sql)
        queryset = self.cursorObj.fetchone()
        CityNo = queryset[0]
        return CityNo

    def post(self):
        Result = dict(Result="Success")
        if request.json:
            self.BDevID = request.json.get('B1DEVICEID', None)
            self.IPAddress = request.json.get('RANIPADDRESS', None)
        CityNo = self.GetCityNode()
        if not CityNo:
            CityNo = '0000'
            Result['Result'] = 'Failure'
            Result['Errordetail'] = "地市区号信息为空"
        IPAddressArr = self.IPAddress.split('.')
        IPList = list(map(lambda x:x.zfill(3),IPAddressArr))
        IPStr = ''.join(IPList)
        NETWORKENTITY = "86." + CityNo + "." + IPStr[0:4] + "." + IPStr[4:8] + "." + IPStr[8:12]
        if Result.get('Errordetail',None):
            Result['NETWORKENTITY'] = ""
            return Result
        else:
            Result['NETWORKENTITY'] = NETWORKENTITY
            return Result

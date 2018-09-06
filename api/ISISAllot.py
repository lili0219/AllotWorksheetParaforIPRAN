from flask_restful import Resource
from flask import request
from config import DBMap

class ISISAllot(Resource):
    def __init__(self):
        self.DBSession = DBMap.get('DBSession', None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.BDevID = None
        self.BPort = None

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
        LspID = None
        Result = dict(Result="Success")
        if request.json:
            self.BDevID = request.json.get('B1DEVICEID', None)
            self.BPort = request.json.get('B1PORT', None)
        if self.BDevID == None or self.BPort == None:
            Result['Result'] = 'Failure'
            Result['Errordetail'] = "NETWORKENTITY生成失败"
        statement = "select igp.lspid \
          from IGPRouDevice igp, devaddr de \
         where 1 = 1 \
           and igp.ipaddress = de.ipaddress \
           and de.deviceid = igp.roudeviceid \
           and igp.roudeviceid = '{BDevID}' \
           and de.intdescr = '{BPort}'".format(BDevID=self.BDevID,BPort=self.BPort)
        self.cursorObj.execute(statement)
        queryset = self.cursorObj.fetchone()
        if queryset:
            LspID = int(queryset[0])
        else:
            statement = "select  max(igp.lspid)  from   IGPRouDevice igp where igp.roudeviceid = '{BDevID}'".\
                format(BDevID=self.BDevID)
            self.cursorObj.execute(statement)
            queryset = self.cursorObj.fetchone()
            if queryset[0]:
                LspID = int(queryset[0]) + 1
            else:
                LspID = 1
            statement = "insert into IGPRouDevice(roudeviceid,Lspid,,Ipaddress,Createtime) values \
            (:BDevID,:Lspid,:Intdescr,sysdate)"
            self.cursorObj.execute(statement,{"BDevID":self.BDevID,"Lspid":LspID,",Ipaddress":""})
            self.DBSession.commit()
        if Result.get('Errordetail',None):
            Result['ISIS'] = ""
            return Result
        else:
            Result['ISIS'] = LspID
            return Result

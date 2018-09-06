from flask_restful import Resource
from flask import request
from config import DBMap

class LOOPID(Resource):
    def __init__(self):
        self.DBSession = DBMap.get('DBSession', None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.B1DevID = None
        self.B1Port = None
        self.B2DevID = None
        self.B2Port = None

    def post(self):
        Result = dict(Result="Success")
        AreaID = None
        if request.json:
            self.B1DevID = request.json.get("B1DEVICEID",None)
            self.B1Port = request.json.get("B1PORT",None)
            self.B2DevID = request.json.get("B2DEVICEID",None)
            self.B2Port = request.json.get("B2Port",None)
        if self.B1DevID and self.B1Port:
            statement = "select areaid from ipranareaidinfo where b1deviceid='{B1DevID}' and b1port='{B1Port}'".format(\
                B1DevID = self.B1DevID,B1Port = self.B1Port)
            self.cursorObj.execute(statement)
            queryset = self.cursorObj.fetchone()
            if queryset:
                AreaID = queryset[0]
            else:
                AreaID = '0.0.0.1'
            statement = "insert into IPRANAREAIDINFO(B1DEVICEID,B1PORT,B2DEVICEID,B2PORT,AREAID,STATUS) VALUES \
            (:B1DevID,:B1Port,:B2DevID,:B2Port,:AreaID,'using')"
            param = {"B1DevID":self.B1DevID,"B1Port":self.B1Port,"B2DevID":self.B2DevID,"B2Port":self.B2Port,"AreaID":AreaID}
            self.cursorObj.execute(statement,param)
            self.DBSession.commit()
            Result["LOOPID"] = AreaID
            Result["Errordetail"] = ""
        else:
            Result["Result"] = "Failure"
            Result["LOOPID"] = ""
            Result["Errordetail"] = "LOOPID生成失败"
        return Result

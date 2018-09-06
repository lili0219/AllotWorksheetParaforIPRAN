from flask_restful import Resource
from flask import request
from functools import reduce
from config import DBMap
from .logger import setup_logging
import logging
import re
import traceback

setup_logging(default_path = "logging.yaml")
class AssignAddress(Resource):
    """
    分配地址
    """
    def __init__(self):
        self.DBSession = DBMap.get('DBSession',None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.BDevID = ''
        self.OCCUPANCY = ''
        self.MVendor  = ''
        self.IPTYPE   = ''
        self.IPSegment = dict()
        self.IPUsedSegment = dict()
        self.IPTypeArr = list()

    def GetCityNode(self):
        """
        根据B设备ID获取地市节点信息
        :return:
        """
        sql = """select substr(n.nodefullcode,
                                  instr(n.nodefullcode,
                                        '.',
                                        1,
                                        (select sy.paravalue
                                           from syspara sy
                                          where sy.paraname = 'CITYLEVEL')) - 6,6
                                        ),
                           n.nodecode,
                           n.nodefullcode
                      from node n, device d
                     where d.nodecode = n.nodecode
                       and d.changetype = 0
                       and d.deviceid = '{BDevID}'""".format(BDevID=self.BDevID)
        self.cursorObj.execute(sql)
        queryset = self.cursorObj.fetchone()
        nodecode = queryset[0]
        return nodecode

    def GetIPSegment(self,NodeCode):
        """
        获取Nodecode对应地市地址段范围
        :param NodeCode:
        :return:
        """
        sql = """select nodecode,
                        beginip,
                        endip,
                        iptype,
                        nbeginip,
                        nendip,
                        vendor 
                    from ipranipsegmentcity where nodecode='{NodeCode}'""".format(NodeCode=NodeCode)
        self.cursorObj.execute(sql)
        querysets = self.cursorObj.fetchall()
        for queryset in querysets:
            if queryset[6] == self.MVendor and queryset[3] in self.IPTypeArr:
                self.IPSegment.update({queryset[3]:{'BEGINIP':queryset[1],'ENDIP':queryset[2],\
                                                    'NBEGINIP':queryset[4],'NENDIP':queryset[5]}})
            elif queryset[6] is None and queryset[3] not in self.IPSegment and queryset[3] in self.IPTypeArr:
                self.IPSegment.update({queryset[3]: {'BEGINIP': queryset[1], 'ENDIP': queryset[2],\
                                                     'NBEGINIP': queryset[4], 'NENDIP': queryset[5]}})

    def GetIPUsedSegment(self,nodecode):
        for IPType in self.IPTypeArr:
            sql = """select ipu.ipaddress
                from ipranipusedinfo ipu
                where ipu.nbeginip >= '{NBeginIP}'
                and ipu.nendip <= '{NEndIP}'
                union
                select de.ipaddress
                  from devaddr de
                 where iptonumber(de.ipaddress) between '{NBeginIP}' and '{NEndIP}'
                union
                select de.loopaddress
                  from device de
                 where (iptonumber(de.loopaddress) between '{NBeginIP}' and '{NEndIP}')
                union
                select de.ranloopaddress
                  from device de
                 where (iptonumber(de.ranloopaddress) between '{NBeginIP}' and '{NEndIP}')
                union
                select de.ranloopaddress2
                  from device de
                 where (iptonumber(de.ranloopaddress2) between '{NBeginIP}' and '{NEndIP}')
                union
                select de.neip
                  from device de
                 where (iptonumber(de. neip) between '{NBeginIP}' and '{NEndIP}')""".format(NBeginIP=self.IPSegment[IPType]['NBEGINIP'],
                                                                                             NEndIP=self.IPSegment[IPType]['NENDIP'])
            self.cursorObj.execute(sql)
            querysets = self.cursorObj.fetchall()
            for queryset in querysets:
                ip = queryset[0]
                m = re.match(r'(\S+)/(\d+)',queryset[0])
                if m:
                    #当分配地址是互联地址的时候
                    ip = m.group(1)
                    mask = m.group(2)
                    IPNum = reduce(lambda x, y: int(x) * 256 + int(y), ip.split('.'))
                    tmp = 2 ** (32 - int(mask))
                    IPNum = IPNum - IPNum%tmp
                    for i in range(0,tmp):
                        self.IPUsedSegment.update({IPNum+1:1})
                else:
                    IPNum = reduce(lambda x,y:int(x)*256+int(y),ip.split('.'))
                    #IPNum = IPNum - IPNum%4
                    self.IPUsedSegment.update({IPNum:1})

    def GetIPRule(self):
        sql = """select sy.PARAVALUE from syspara sy where sy.paraname = 'IPRANIPUNIQUE'"""
        self.cursorObj.execute(sql)
        queryset = self.cursorObj.fetchone()
        if queryset:
            return queryset[0]
        else:
            return 'Y'

    def post(self):
        #获取分配接口的参数
        Result = {}
        if request.json:
            self.BDevID = request.json.get('B1DEVICEID',None)
            self.OCCUPANCY = request.json.get('OCCUPANCY',None)
            self.MVendor = request.json.get('MVDENDOR',None)
            self.IPTYPE = request.json.get('IPTYPE',None)
            self.IPTypeArr = self.IPTYPE.split(',')
        if not self.BDevID:
            Result['Result'] = 'Failure'
            Result['Errordetail'] = "发送的数据不全"
            return Result
        try:
            #获取地市节点
            NodeCode = self.GetCityNode()
            self.GetIPSegment(NodeCode)
            self.GetIPUsedSegment(NodeCode)
            IPRule = self.GetIPRule()
            # self.IPTypeArr = self.IPTYPE.split(',')
            IPFirstNum = {}
            TempResult = {}  # 存放分配出来的地址段对应的10进制数

            Result['Result'] = 'Success'
            if IPRule == 'Y' and 'mgmtLoopback' in self.IPTypeArr and 'servLoopback' in self.IPTypeArr:
                m = re.match(r"(\d+)\.(\S+)", self.IPSegment['mgmtLoopback']['BEGINIP'])
                if m:
                    IPFirstNum['mgmtLoopback'] = m.group(1)
                s = re.match(r"(\d+)\.(\S+)", self.IPSegment['servLoopback']['BEGINIP'])
                if s:
                    IPFirstNum['servLoopback'] = m.group(1)

            for IPType in self.IPTypeArr:
                Result[IPType] = ''
                func = lambda x: '.'.join([str(int(x / (256 ** i) % 256)) for i in range(3, -1, -1)])
                m = re.search(r'Link',IPType)
                if m:
                    for IPNum in range(self.IPSegment[IPType]['NBEGINIP'],self.IPSegment[IPType]['NENDIP'],4):
                        tmp = IPNum - IPNum % 4
                        for i in range(tmp,tmp+4):
                            if i in self.IPUsedSegment:
                                break
                        else:
                            #占用已经分配的地址
                            for i in range(tmp, tmp + 4):
                                self.IPUsedSegment.update({tmp:1})
                            Result[IPType] = func(int(tmp)) + '/30'
                            break
                    else:
                        Result['Result'] = 'Failure'
                        Result['Errordetail'] = "{IPType}无空闲地址".format(IPType=IPType)
                        break
                elif IPRule == 'N' and not Result.get(IPType,None):
                    for IPNum in range(self.IPSegment[IPType]['NBEGINIP'],self.IPSegment[IPType]['NENDIP']):
                        if IPNum not in self.IPUsedSegment:
                            self.IPUsedSegment.update({IPNum:1})
                            Result[IPType] = func(int(IPNum))
                            break
                    else:
                        Result['Result'] = 'Failure'
                        Result['Errordetail'] = "{IPType}无空闲地址".format(IPType=IPType)
                        break
                else:
                    for IPNum in range(self.IPSegment[IPType]['NBEGINIP'], self.IPSegment[IPType]['NENDIP']):
                        # IPNum = IPNum - IPNum%4
                        if IPNum not in self.IPUsedSegment:
                            # 获取IP后面3位数字的和
                            CommNum = int(IPNum) - int(IPFirstNum[Type]) * 256 ** 3
                            for Type in self.IPTypeArr:
                                if IPType == Type:
                                    continue
                                else:
                                    SumNum = CommNum + int(IPFirstNum[IPType]) * 256 ** 3
                                    # 判断IP是否已经被占用
                                    if SumNum in self.IPUsedSegment:
                                        break
                                    TempResult[Type] = SumNum
                            else:
                                TempResult[IPType] = IPNum
                                break
                func = lambda x: '.'.join([str(int(x / (256 ** i) % 256)) for i in range(3, -1, -1)])
                for IPType, IPNum in TempResult.items():
                    Result[IPType] = func(int(IPNum))
                Result['Result'] = 'Success'
        except Exception as e:
            Result['Result'] = 'Failure'
            raise e
        finally:
            if Result.get("Result",None) == 'Success':
                statement = "insert into IPRANIPUSEDINFO(nbeginip,nendip,ipaddress,iptypedetail,status,occupancy \
                ,portid,remark) VALUES (:nbeginip,:nendip,:ipaddress,:iptype,:status,:occupancy,:portid,:remark)"
                statement1 = "insert into IPRANIPUsedHis(nbeginip,nendip,ipaddress,iptypedetail,occupancy,\
                portid,remark,time,CHANGETYPE) VALUES (:nbeginip,:nendip,:ipaddress,:iptype,:occupancy,:portid,\
                :remark,sysdate,'add')"
                #self.cursorObj.prepare(statement)
                for IPType in self.IPTypeArr:
                    IPSeg = Result.get(IPType,None)
                    if IPSeg:
                        m = re.match(r'(\S+)/(\d+)',IPSeg)
                        if m:
                            Ip = m.group(1)
                            Mask = m.group(2)
                            IPNum = reduce(lambda x, y: int(x) * 256 + int(y), Ip.split('.'))
                            Nbeginip = IPNum - IPNum % (2**(32-int(Mask)))
                            Nendip = Nbeginip + 2 ** (32-int(Mask)) - 1
                        else:
                            IPNum = reduce(lambda x, y: int(x) * 256 + int(y), IPSeg.split('.'))
                            Nbeginip = IPNum - IPNum % (2 ** (32 - int(Mask)))
                            Nendip = Nbeginip + 2 ** (32 - int(Mask)) - 1
                    self.cursorObj.prepare(statement)
                    self.cursorObj.execute(None,{'nbeginip':Nbeginip,'nendip':Nendip,'ipaddress':IPSeg,'iptype':IPType,\
                                                 'status':'using','occupancy':self.OCCUPANCY,'portid':'','remark':''})
                    self.cursorObj.prepare(statement1)
                    self.cursorObj.execute(None,{'nbeginip':Nbeginip,'nendip':Nendip,'ipaddress':IPSeg,'iptype':IPType,\
                                                 'occupancy':self.OCCUPANCY,'portid':'','remark':''})
                self.DBSession.commit()
            if self.cursorObj is not None:
                self.cursorObj.close()
            return Result

class AlterIPAddress(AssignAddress):
    """
    修改地址接口
    """
    def __init__(self):
        self.DBSession = DBMap.get('DBSession',None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.BDevID = ''
        self.OCCUPANCY = ''
        self.MVendor  = ''
        self.IPTYPE   = ''
        self.IPADDRESS = None
        self.IPTypeArr = list()
        self.IPSegment = dict()

    def IsUsed(self,ip):
        IsUsed = 'N'
        if re.search(r'Link',self.IPTYPE):
            m = re.match(r'(\S+)/(\d+)',self.IPADDRESS)
            if m:
                Ip = m.group(1)
                Mask = m.group(2)
            else:
                Ip = self.IPADDRESS
                Mask = 30
        else:
            Ip = self.IPADDRESS
            Mask = 32
        IPNum = reduce(lambda x,y:int(x)*256+int(y),Ip.split('.'))
        IPNum = IPNum - IPNum%(2**(32-int(Mask)))
        func = lambda x: '.'.join([str(int(x / (256 ** i) % 256)) for i in range(3, -1, -1)])

        for num in range(IPNum,IPNum+2**(32-int(Mask))):
            Ip = func(num)
            statement = statement = """select ipu.ipaddress from ipranipusedinfo  ipu where ipu.ipaddress='{IP}'
                        union 
                        select ipu.ipaddress from ipranipusedinfo  ipu where ipu.ipaddress='{IP1}'
                        union
                        select de.ipaddress from devaddr de where de.ipaddress='{IP}'
                        union
                        select de.loopaddress from device de where de.loopaddress='{IP}'
                        union 
                        select de.ranloopaddress from device de where de.ranloopaddress='{IP}'
                        union 
                        select de.ranloopaddress2 from device de where de.ranloopaddress2='{IP}'
                        union 
                        select de.neip from device de where de.neip='{IP}'""".format(IP=Ip,IP1=ip)
            self.cursorObj.execute(statement)
            queryset = self.cursorObj.fetchone()
            if queryset:
                IsUsed = 'Y'
                break
        else:
            IsUsed = 'N'
        return IsUsed

    def post(self):
        Result = {}
        if request.json:
            self.BDevID = request.json.get('B1DEVICEID', None)
            self.OCCUPANCY = request.json.get('OCCUPANCY', None)
            self.MVendor = request.json.get('MVENDOR', None)
            self.IPTYPE = request.json.get('IPTYPE', None)
            self.IPADDRESS = request.json.get('IPADDRESS',None)
            self.IPTypeArr = self.IPTYPE.split(',')
        IsUsed = self.IsUsed(self.IPADDRESS)
        IpRule = self.GetIPRule()
        if IsUsed == 'Y':
            Result['Result'] = 'Failure'
            Result['Errordetail'] = '{IP}地址已经被占用'.format(IP=self.IPADDRESS)
        else:
            NodeCode = self.GetCityNode()
            self.GetIPSegment(NodeCode)
            m = re.match(r'(\S+)/(\d+)',self.IPADDRESS)
            if m:
                Ip = m.group(1)
                Mask = m.group(2)
            else:
                Ip = self.IPADDRESS
                Mask = 32
            IPNum = reduce(lambda x,y:int(x)*256+int(y),Ip.split('.'))
            statement = "update ipranipusedinfo set NBeginIP=:nbeginip,NEndIP=:nendip,IPAddress=:ipaddress,\
                            Remark=:remark \
                      where OCCUPANCY=:occupancy and IPTypeDetail=:iptype"
            statement1 = "update ipranipusedhis set NBeginIP=:nbeginip,NEndIP=:nendip,IPAddress=:ipaddress,\
                                        ChangeType='mod',Remark=:remark,time=sysdate\
                                  where OCCUPANCY=:occupancy and IPTypeDetail=:iptype"
            statement2 = "select NBEGINIP,NENDIP,IPADDRESS,IPTYPEDETAIL,STATUS,OCCUPANCY,PORTID,REMARK \
                      from IPRANIPUSEDINFO \
                      where OCCUPANCY='{OCCUPANCY}' \
               and IPTypeDetail='{IPType}'".format(OCCUPANCY=self.OCCUPANCY,IPType=self.IPTYPE)
            self.cursorObj.execute(statement2)
            queryset = self.cursorObj.fetchone()
            if queryset:
                Original = queryset[2]
            if self.IPSegment[self.IPTYPE]['NBEGINIP'] < IPNum < self.IPSegment[self.IPTYPE]['NENDIP']:
                param = dict()
                if Mask == 32:
                    remark = "{Original}改成{Current}".format(Original=Original,Current=self.IPADDRESS)
                    param = dict(nbeginip = IPNum,nendip = IPNum,ipaddress = Ip,iptype = self.IPTYPE,
                                 remark=remark,occupancy=self.OCCUPANCY)
                else:
                    nbeginip = IPNum - IPNum%(2**(32-int(Mask)))
                    nendip = IPNum + 2**(32-int(Mask))
                    remark = "{Original}改成{Current}".format(Original=Original, Current=self.IPADDRESS)
                    param = dict(nbeginip=nbeginip, nendip=nendip, ipaddress=Ip+"/"+Mask, iptype=self.IPTYPE,
                                  remark=remark, occupancy=self.OCCUPANCY)
                if IpRule == 'N' or self.MVendor == 'HU' or self.IPTYPE == 'servLinkIP':
                    Result[self.IPTYPE] = self.IPADDRESS
                    Result['Result'] = 'Success'
                    self.cursorObj.execute(statement,param)
                    self.cursorObj.execute(statement1,param)
                    self.DBSession.commit()
                else:
                    if self.IPTYPE == 'mgmtLoopback':
                        m = re.match(r'(\d+)\.(\S+)',self.IPSegment[self.IPTYPE]['nbeginip'])
                        s = re.match(r'(\d+)\.(\S+)', self.IPADDRESS)
                        IPFirst = m.group(1)
                        Ip = IPFirst + "." + s.group(2)
                        IsUsed = self.IsUsed(Ip)
                        if IsUsed == 'Y':
                            Result['Result'] = 'Failure'
                            Result['Errordetail'] = '{IP}地址已经被占用'.format(IP=Ip)
                        else:
                            Result['Result'] = 'Success'
                            Result['mgmtLoopback'] = self.IPADDRESS
                            Result['servLoopback'] = Ip
                    elif self.IPTYPE == 'servLoopback':
                        m = re.match(r'(\d+)\.(\S+)', self.IPSegment[self.IPTYPE]['nbeginip'])
                        s = re.match(r'(\d+)\.(\S+)', self.IPADDRESS)
                        IPFirst = m.group(1)
                        Ip = IPFirst + "." + s.group(2)
                        IsUsed = self.IsUsed(Ip)
                        if IsUsed == 'Y':
                            Result['Result'] = 'Failure'
                            Result['Errordetail'] = '{IP}地址已经被占用'.format(IP=Ip)
                        else:
                            Result['Result'] = 'Success'
                            Result['servLoopback'] = self.IPADDRESS
                            Result['mgmtLoopback'] = Ip
                    else:
                        Result['Result'] = 'Success'
                        Result[self.IPType] = self.IPADDRESS

                    if Result['Result'] == 'Success':
                        for k,v in Result.items():
                            if k in ('servLoopback','mgmtLoopback') and k != self.IPTYPE:
                                Ip = Result[k]
                                IPNum = reduce(lambda x, y: int(x) * 256 + int(y), Ip.split('.'))
                                remark = "{Original}改成{Current}".format(Original='1.1.1.1', Current=self.IPADDRESS)
                                param = dict(nbeginip=IPNum, nendip=IPNum, ipaddress=Ip, iptype=k,
                                             changetype='mod', remark=remark, occupancy=self.OCCUPANCY)
                                self.cursorObj.execute(statement, param)
                                self.cursorObj.execute(statement1, param)
                                self.DBSession.commit()
            else:
                Result['Result'] = 'Failure'
                Result['Errordetail'] = '{IP}地址不在范围内'.format(IP=self.IPADDRESS)
        return Result

class RecoverIPAddress(Resource):
    """
    回收地址
    """
    def __init__(self):
        self.DBSession = DBMap.get('DBSession',None)
        if self.DBSession:
            self.cursorObj = self.DBSession.cursor()
        else:
            self.cursorObj = None
        self.OCCUPANCY = ''
        self.IPTYPE   = ''
        self.IPADDRESS = ''
        self.IPTypeArr = list()

    def post(self):
        Result = {}
        if request.json:
            self.OCCUPANCY = request.json.get('OCCUPANCY',None)
            self.IPADDRESS = request.json.get('IPADDRESS',None)
            self.IPTYPE    = request.json.get('IPTYPE',None)

        statement = """select NBEGINIP,NENDIP,IPADDRESS,IPTYPEDETAIL,STATUS,OCCUPANCY,PORTID,REMARK from IPRANIPUSEDINFO
              where OCCUPANCY='{OCCUPANCY}'""".format(OCCUPANCY=self.OCCUPANCY)
        if self.IPTYPE:
            statement = statement + " and IPTYPEDETAIL='{IPTYPE}'".format(IPTYPE=self.IPTYPE)
        statement1 = """insert into IPRANIPUSEDHIS(NBEGINIP,NENDIP,IPADDRESS,IPTYPEDETAIL,OCCUPANCY,CHANGETYPE,\
        TIME,REMARK) VALUES (:nbeginip,:nendip,:ipaddress,:iptype,:occupancy,'del',sysdate,'工单作废回收')"""
        try:
            if self.OCCUPANCY != None:
                self.cursorObj.execute(statement)
                querysets = self.cursorObj.fetchall()
                for queryset in querysets:
                    param = {'nbeginip':queryset[0],'nendip':queryset[1],'ipaddress':queryset[2],'iptype':queryset[3],
                             'occupancy':queryset[5]}
                    self.cursorObj.execute(statement1,param)
                    self.DBSession.commit()
                para = dict(occupancy=self.OCCUPANCY)
                #statement = """delete from IPRANIPUSEDINFO where OCCUPANCY=:occupancy"""
                statement = "delete from IPRANIPUSEDINFO i where i.OCCUPANCY=:occupancy"
                if self.IPTYPE:
                    statement = statement + """ and i.IPTYPEDETAIL=:iptype"""
                    para['iptype'] = self.IPTYPE
                #self.cursorObj.prepare(statement)
                rows = self.cursorObj.execute(statement,para)
                self.DBSession.commit()
                Result['Result'] = 'Success'
                Result['Errordetail'] = ""
            else:
                Result['Result'] = 'Failure'
                Result['Errordetail'] = "地址没有被预占"
        except Exception as e:
            traceback.print_exc()
        finally:
            return Result
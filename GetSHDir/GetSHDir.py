import os,subprocess,sys
import re
import logging
import xml.sax

logging.basicConfig(level=logging.INFO,format='(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger(__name__)

Para = dict()

class XMLHandler(xml.sax.ContentHandler):
    global Para
    def __init__(self,ParaName):
        self.ParaName = ParaName
        self.LastData = ""
        self.CurrentData = ""
        self.Tag = ''
        self.TagValue = ''
    def startDocument(self):
        logging.info("XML开始解析中...")
    #元素开始事件处理
    def startElement(self, name, attrs):
        self.CurrentData = name

    #元素结束事件处理
    def endElement(self, name):
        if self.CurrentData == "ParaName" and self.Tag == self.ParaName:
            self.LastData = self.Tag
        elif self.CurrentData == "ParaValue" and self.LastData:
            Para.update({self.LastData:self.TagValue})
            self.LastData = ""
            #Para[self.LastData] = self.TagValue
        self.CurrentData = ""

    #内容处理函数
    def characters(self, content):
        if self.CurrentData == "ParaName":
            self.Tag = content
        elif self.CurrentData == "ParaValue":
            self.TagValue = content

    def endDocument(self):
        logging.info("XML文档解析结束!")

class GetSHDir(object):
    __author__ = "lixn"
    def __init__(self):
        #self.Paraname = Paraname
        self.HomeDir  = os.getenv('HOME',None)
        self.configfile = self.getfilename()

    def getfilename(self):
        """
        获取文件名称
        :return:
        bytes->str:decode str->bytes:encode
        """
        platform = sys.platform
        if not self.HomeDir and not re.search( r'win', platform, re.M|re.I):
            p = subprocess.Popen("whoami",shell=True,stdout=subprocess.PIPE)
            out = p.stdout.read()
            if out:
                self.HomeDir = "/" + out.decode()
        if self.HomeDir:
            return self.HomeDir + "/nms/cfg/shconfig.xml"
        elif re.search( r'win', platform, re.M|re.I):
            return "E://Project/movie_project/AllotWorksheetParaforIPRAN/GetSHDir/shconfig.xml"

    def dealfilename(self,Paraname):
        handler = XMLHandler(Paraname)
        parser  = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        parser.setContentHandler(handler)
        parser.parse(self.configfile)
        if Paraname in Para:
            ParaValue = Para.get(Paraname,None)
            logging.info("Paraname:{paraname} Paravalue:{paravalue}".format(paraname=Paraname,paravalue=ParaValue))
            return ParaValue
        else:
            return None

if __name__ == '__main__':
    obj = GetSHDir()
    ISNOTFlag = obj.dealfilename("DB_Python")
    logging.info("DB_Python: {}".format(ISNOTFlag))
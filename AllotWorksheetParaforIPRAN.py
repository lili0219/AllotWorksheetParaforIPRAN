from flask import Flask,request,jsonify,json
from flask_restful import Api,Resource,reqparse
from decorator import ReConnectDB
from config import DB_URL,DBType
from decorator import DBMap
from api.AddrManager import AssignAddress,AlterIPAddress,RecoverIPAddress
from api.NETWORKENTITY import NETWORKENTITY
from api.ISISAllot import ISISAllot

app = Flask(__name__)
api = Api(app=app,decorators=[ReConnectDB(DBMap=DBMap,DB_URL=DB_URL,DBType=DBType),])

USER_LIST = {
    '1': {'name':'Michael'},
    '2': {'name':'Tom'},
}

@app.route('/')
#@ReConnectDB(DBMap=DBMap,DB_URL=DB_URL,DBType=DBType)
def hello_world():
    return 'Hello World!'

class UserList(Resource):
    def get(self):
        print("DBMap:",type(request.args),request.json)
        return USER_LIST

    def post(self):
        m = {
            "name":"lixn",
            "age":25
        }
        return m

api.add_resource(UserList, '/users')
api.add_resource(ISISAllot, '/ISISAllot')
api.add_resource(NETWORKENTITY, '/NETWORKENTITY')
api.add_resource(AssignAddress, '/assignaddress')
api.add_resource(AlterIPAddress, '/alteraddress')
api.add_resource(RecoverIPAddress, '/recoveripaddress')

if __name__ == '__main__':
    app.run(debug=True)

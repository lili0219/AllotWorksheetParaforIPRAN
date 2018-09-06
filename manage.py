from flask_migrate import MigrateCommand,Migrate
from flask_script import Server,Manager
from AllotWorksheetParaforIPRAN import app

manager = Manager(app)

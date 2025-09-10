from flask import Flask

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)


# Initialize extensions
from models.models import db
db.init_app(app)
login_manager = LoginManager(app)
mail = Mail(app)
migrate = Migrate(app, db)

# Import blueprints

from routes.auth import auth_bp
from routes.handover import handover_bp
from routes.dashboard import dashboard_bp
from routes.roster import roster_bp

from routes.team import team_bp
from routes.roster_upload import roster_upload_bp
from routes.reports import reports_bp



# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(handover_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(roster_bp)
app.register_blueprint(team_bp)
app.register_blueprint(roster_upload_bp)
app.register_blueprint(reports_bp)
from routes.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

from routes.escalation_matrix import escalation_bp
app.register_blueprint(escalation_bp)

# Register user management blueprint
from routes.user_management import user_mgmt_bp
app.register_blueprint(user_mgmt_bp)

# Register keypoints updates blueprint
from routes.keypoints import keypoints_bp
app.register_blueprint(keypoints_bp)

@login_manager.user_loader
def load_user(user_id):
    from models.models import User
    return User.query.get(int(user_id))

if __name__ == "__main__":
    app.run(debug=True)

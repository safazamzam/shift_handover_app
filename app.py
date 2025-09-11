from flask import Flask

from services.audit_service import log_action

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Log every page/tab visit
@app.before_request
def log_page_visit():
    from flask_login import current_user
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        log_action('Page Visit', f'Visited {request.path}')


# Initialize extensions
from models.models import db
db.init_app(app)
login_manager = LoginManager(app)
mail = Mail(app)
migrate = Migrate(app, db)

# Import blueprints

from routes.auth import auth_bp

# Patch login/logout to log actions
from flask import request
from flask_login import login_user, logout_user
import routes.auth
orig_login_user = login_user
orig_logout_user = logout_user
def patched_login_user(user, *args, **kwargs):
    log_action('Login', f'User {getattr(user, "username", user)} logged in')
    return orig_login_user(user, *args, **kwargs)
def patched_logout_user(*args, **kwargs):
    log_action('Logout', f'User {getattr(current_user, "username", current_user)} logged out')
    return orig_logout_user(*args, **kwargs)
routes.auth.login_user = patched_login_user
routes.auth.logout_user = patched_logout_user
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

# Register misc blueprint for 'coming soon' tabs
from routes.misc import misc_bp
app.register_blueprint(misc_bp)

# Register audit logs blueprint
from routes.logs import logs_bp
app.register_blueprint(logs_bp)

# Register KB details blueprint
from routes.kb_details import bp as kb_details_bp
app.register_blueprint(kb_details_bp)

# Register vendor details blueprint
from routes.vendor_details import bp as vendor_details_bp
app.register_blueprint(vendor_details_bp)

# Register application details blueprint
from routes.application_details import bp as application_details_bp
app.register_blueprint(application_details_bp)

@login_manager.user_loader
def load_user(user_id):
    from models.models import User
    return User.query.get(int(user_id))

if __name__ == "__main__":
    app.run(debug=True)

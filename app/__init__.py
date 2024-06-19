from flask import Flask
import dash
import dash_bootstrap_components as dbc
from flask_dynamodb_sessions import Session
import logging

from .config import USE_AWS
from .data.user_management import login_manager

# this function sets up the logging configuration
def setup_logging():
    logging.basicConfig(level=logging.DEBUG, filename='debug.log', filemode='w', 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler that logs only higher level messages
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


setup_logging()


# Initialize Flask application for ElasticBeanstalk deployment
# This may not be the best actual way to deploy this, but it is what we've tried
application = Flask(__name__)
application.secret_key = 'development-server-secret-key-TODO!!-fix-this-for-production'
application.config["SESSION_COOKIE_SECURE"] = False  #!!TODO: change this for production to True


if USE_AWS:
    # This will use DynamoDB for the session when deployed to AWS
    # by taking advantage of the flask_dynamodb_sessions library
    # otherwise, we'll just use the default flask session
    Session(application)

login_manager.init_app(application)

# Initialize Dash application with Flask as server
app = dash.Dash(__name__, server=application, title="SegBuilder",
                url_base_pathname='/segbuilder/', external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

# Importing layouts and callbacks after app initialization to avoid circular imports
from .layouts import main_layout
from .callbacks import register_callbacks


register_callbacks(app)

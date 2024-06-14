from .auth_callbacks import register_auth_callbacks
from .data_callbacks import register_data_callbacks
from .ui_callbacks import register_ui_callbacks

def register_callbacks(app):
    register_auth_callbacks(app)
    register_data_callbacks(app)
    register_ui_callbacks(app)
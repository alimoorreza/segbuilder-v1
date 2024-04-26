from app import app, application
from .layouts.main_layout import get_main_layout

def setup_app():
    # may need to add any server configurations or conditions to set the layout
    app.layout = get_main_layout()



# run the app.
if __name__ == "__main__":
    setup_app()
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    application.run(host="0.0.0.0")

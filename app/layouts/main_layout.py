from dash import html
import dash_bootstrap_components as dbc

# Import other layout functions
from .login_layout import get_login_layout
from .segbuilder_layout import get_segbuilder_layout
from .password_change_modal import get_password_change_modal

def get_main_layout():
    """
    Returns the main layout of the application.

    This layout includes the header, password change modal, login content, and main content for the SegBuilder.
    """
    return html.Div([
        # Header visible on all tabs
        dbc.Row([
            dbc.Col(html.Img(src="assets/eyelogo.png", height=100), width='auto'),
            dbc.Col(children=[
                html.H1(children="SegBuilder"),
                html.H4(children="Machine-Assisted Semantic Segmentation Annotation"),
            ]),
            dbc.Col(children=[
                html.H6("User: None ", id="username-display"),
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem("Change Password", id="initiate-change-password-button", n_clicks=0),
                    dbc.DropdownMenuItem("Logout", id="logout-button", n_clicks=0),
                ], label=(html.I(className="bi bi-person-lines-fill"))),
            ], style={"textAlign": "right", "paddingRight": "30px", "paddingTop": "20px"})
        ]),

        #password change modal
        get_password_change_modal(),

        # Login content section with spinner
        dbc.Spinner(html.Div(get_login_layout(), id='login-content', style={"display": "block"}), color="primary"),
        # Main content section for SegBuilder UI
        html.Div(get_segbuilder_layout(), id='main-content', style={"display": "none"})
    ])

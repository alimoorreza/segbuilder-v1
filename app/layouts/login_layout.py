from dash import html
import dash_bootstrap_components as dbc

def get_login_layout():
    """
    Returns the layout for the login page.

    This layout consists of a container with a card that includes form elements for username and password input, 
    an error message display, and a login button.
    """
    return html.Div([
        dbc.Container([
            dbc.Card([
                # Error message display for invalid login attempts
                dbc.FormText('Invalid username or password.', color="danger", id="invalid-password-message", style={'display': "none"}),
                
                # Label and input field for username
                dbc.Label('Username'),
                dbc.Input(id='login-username', placeholder='Enter username'),

                # Label and input field for password
                dbc.Label('Password'),
                dbc.Input(id='login-password', type='password', placeholder='Enter password'),
                html.Br(),

                # Login button
                dbc.Button('Login', id='login-button', color='primary')
            ], body=True, class_name="p-3") # Card with padding
        ], class_name='mt-5 d-inline-flex justify-content-center') # Container with margin and centered alignment
    ])
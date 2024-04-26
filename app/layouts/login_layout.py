from dash import html
import dash_bootstrap_components as dbc

def get_login_layout():
    return html.Div([
        dbc.Container([
            dbc.Card([
                dbc.FormText('Invalid username or password.', color="danger", id="invalid-password-message", style={'display': "none"}),
                dbc.Label('Username'),
                dbc.Input(id='login-username', placeholder='Enter username'),
                dbc.Label('Password'),
                dbc.Input(id='login-password', type='password', placeholder='Enter password'),
                html.Br(),
                dbc.Button('Login', id='login-button', color='primary')
            ], body=True, class_name="p-3")
        ], class_name='mt-5 d-inline-flex justify-content-center')
    ])
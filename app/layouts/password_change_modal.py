from dash import html
import dash_bootstrap_components as dbc

def get_password_change_modal():
    """
    Returns the layout for the password change modal.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader("Change Password"),
            dbc.ModalBody(
                dbc.Form(
                    [
                        html.Div(
                            [
                                dbc.Label("Current Password", className="mr-2"),
                                dbc.Input(type="password", id="current-password"),
                            ],
                            className="mr-3",
                        ),
                        html.Div(
                            [
                                dbc.Label("New Password", className="mr-2"),
                                dbc.Input(type="password", id="new-password"),
                            ],
                            className="mr-3",
                        ),
                        html.Div(
                            [
                                dbc.Label("Confirm New Password", className="mr-2"),
                                dbc.Input(type="password", id="confirm-password"),
                            ],
                            className="mr-3",
                        ),
                        dbc.FormText('', color="danger", id="change-password-message"),
                    ]
                )
            ),
            dbc.ModalFooter(
                dbc.Button("Change Password", id="change-password-button", className="ml-auto")
            ),
        ],
        id="password-modal", is_open=False
    )
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash import no_update, callback_context
from flask import session
from dash.exceptions import PreventUpdate
from werkzeug.security import check_password_hash
import logging
from ..data import User, load_user, change_password_in_db, get_user_from_session
from ..utils import populate_project_cards
from ..resources import delete_db_item


logging.basicConfig(filename='/app/logs/app.log', level=logging.DEBUG)

def register_auth_callbacks(app):

    @app.callback(
        Output("password-modal", "is_open"),
        Output("change-password-message","children"),
        Input("change-password-button", "n_clicks"),
        Input("initiate-change-password-button","n_clicks"),
        State("current-password", "value"),
        State("new-password", "value"),
        State("confirm-password", "value"),
        prevent_initial_callback = True
    )
    def update_password(change_n, initiate_n, current_password, new_password, confirm_password):
        username = get_user_from_session()

        # handle the "change password" button click - to intiaite a password change
        if callback_context.triggered_id == "initiate-change-password-button" and initiate_n and initiate_n > 0:

            #just need to make the password change dialog visible
            return True, ""
        
        # handle the actual password change
        elif callback_context.triggered_id == "change-password-button" and change_n and change_n > 0:
            
            user_obj = load_user(username) 
            
            if user_obj and user_obj.check_password(current_password):
                if new_password != confirm_password:
                    return no_update, "passwords do not match"
                else:
                    if change_password_in_db(username, new_password):  
                        return False, ""
                    else:
                        return True, "Error: failed to update password"
            else:
                return no_update, "invalid password"
        return no_update, "error"

    @app.callback(
        Output('username-display','children'),
        Output('login-content','style'),
        Output('main-content','style'),
        Output("invalid-password-message",'style'),
        Output("project-cards","children"),
        Input('login-button', 'n_clicks'),
        Input('new-project-has-been-created','data'),
        Input('logout-button','n_clicks'),
        State('login-username', 'value'),
        State('login-password', 'value'),
        prevent_initial_call = True
    )
    def manage_session(n_clicks, new_proj, logout_n, username, password):
        logging.debug("SBDEBUG: In manage session callback")

        # Handle login button click
        if callback_context.triggered_id == "login-button":
            logging.debug("SBDEBUG: login button triggered")

            if n_clicks and n_clicks > 0:
                user = load_user(username)
                if user and user.check_password(password):

                    logging.debug("SBDEBUG SESSION: setting session['username'] to %s",user.id)
                    session['username'] = user.id
                    logging.debug("SBDEBUG SESSION: now let's see what's in session['username'] to %s",session['username'])

                    logging.debug("SBDEBUG: about to populate project cards")
                    project_cards = populate_project_cards(user.id)
                    logging.debug("SBDEBUG: project cards created, about to return them.")
                    return user.id, {'display':"none"}, {"display":"block"}, {'display':"none"}, project_cards
                else:
                    logging.debug("invalid username/password")
                    return "User: None ", no_update, no_update, {'display':"block"}, no_update
            else:
                raise PreventUpdate
            
        # Handle "new project" button click
        elif callback_context.triggered_id == "new-project-has-been-created" and new_proj:
            username = get_user_from_session()
            project_cards = populate_project_cards(username)
            logging.debug("finished updating new project cards")
            return no_update, no_update, no_update, no_update, project_cards
        
        # Handle logout button click
        elif callback_context.triggered_id == "logout-button":
            if logout_n and logout_n > 0:
                logging.debug("got to logout callback")
                session_id = session.get('session_id')

                # remove the session from the database
                if session_id:
                    delete_db_item("sessions","session_id",session_id)

                session.clear()
                # Clear the session data
                return "User: None ", {"display":"block"}, {'display':"none"}, {'display':"none"}, []
        else:
            logging.debug("uncaught trigger: %s",callback_context.triggered_id)
            raise PreventUpdate

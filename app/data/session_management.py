from flask import session
import logging

def get_user_from_session():
    # Get username from the session
    logging.debug("SBDEBUG: in get_user_from_session")
    logging.debug("***********Entire Session***************")
    logging.debug(session)
    logging.debug("**************************")
    logging.debug(dict(session))
    logging.debug("**************************")
    username = session.get('username')
    #username = session['username']
    logging.debug("SBDEBUG: in get_user_from_session, about to return username %s",username)
    # If the session does not exist or has expired, username will be None.
    # No need to manually check DynamoDB because Flask-DynamoDB-SessionStore
    # takes care of that.

    return username
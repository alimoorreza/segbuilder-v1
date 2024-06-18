from flask import session
import logging

def get_user_from_session():
    """
    Get username from the session

    This is essentially a wrapper for getting the username from the Flask session object
    via session.get('username').

    If the session does not exist or has expired, username will be None.

    If this is configured with USE_AWS, this should sync the session automatically
    on DynamoDB because of the Flask-DynamoDB-SessionStore library we're using.

    """
    #logging.debug("SBDEBUG: in get_user_from_session")
    #logging.debug("***********Entire Session***************")
    #logging.debug(session)
    #logging.debug("**************************")
    #logging.debug(dict(session))
    #logging.debug("**************************")
    username = session.get('username')

    logging.debug("SBDEBUG: in get_user_from_session, about to return username %s",username)


    return username
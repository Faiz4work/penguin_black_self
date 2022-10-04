import pytest
from flask import url_for


def assert_status_with_message(status_code=200, response=None, message=None):
    '''
    Checks to see if a message is contained within a response

    Params:
        status_code (int):   Status code that defaults to 200
        response (str):      Flask response
        message (str):       Message to check for
    '''
    assert response.status_code == status_code
    assert message in str(response.data)


class ViewTestMixin(object):
    '''
    Provides common functionality for testing `view.py` code 
    
    Automatically loads in a session and client
    '''

    @pytest.fixture(autouse=True)    # Automatically uses session and client fixtures; We don't need to explicity use this fixture in our tests
    def set_common_fixtures(self, session, client):
        self.session = session
        self.client = client

    def login(self, identity='admin@local.host', password='password'):
        '''
        Login a specific user

        Returns: Flask response
        '''
        return login(self.client, identity, password)

    def logout(self):
        '''
        Logout a specific user

        Returns: Flask response
        '''
        return logout(self.client)


def login(client, identity='', password=''):
    '''
    Log a specific user in

    Params:
        client:           Flask client
        username (str):   Identity
        password (str):   Password
        
    Returns: Flask response
    '''
    user = dict(identity=identity, password=password)

    response = client.post(url_for('user.login'), data=user, follow_redirects=True)

    return response


def logout(client):
    '''
    Log a specific user out

    Params:
        client: Flask client
        
    Returns: Flask response
    '''
    return client.get(url_for('user.logout'), follow_redirects=True)

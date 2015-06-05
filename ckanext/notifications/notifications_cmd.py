from ckan.lib.cli import CkanCommand
import sys
import logging
import uuid
log = logging.getLogger('ckanext')
log.setLevel(logging.DEBUG)

def make_password():
        # create a hard to guess password
        out = ''
        for n in xrange(8):
            out += str(uuid.uuid4())
        return out

class NotificationsCmd(CkanCommand):
    """ updates existing users to receive notifications
        Usage:
        notifications-cmd update-users
    """
    
    summary = __doc__.split('\n')[0]
    usage = __doc__
    #max_args = 3
    #min_args = 0
    
    def __init__(self, name):
        super(NotificationsCmd, self).__init__(name)
    def command(self):
        self._load_config()
              
        if len(self.args) == 0:
            self.parser.print_usage()
            sys.exit(1)
        cmd = self.args[0]
        if cmd == 'update-users':
            import ckan.plugins.toolkit as toolkit
            import ckan.logic.schema as schema
            log.info('Updating users')
            try:
                users = toolkit.get_action('user_list')(data_dict={})
                #log.info('site users: %s', users)
                for user in users:
                    user_schema = schema.default_user_schema()
                    user_schema['name'] = [toolkit.get_validator('ignore_missing')]
                    user_schema['email'] = [toolkit.get_validator('ignore_missing')]
                    user_schema['password'] = [toolkit.get_validator('ignore_missing')]
                    context = {'schema' : user_schema, 'ignore_auth': True}
                    user_updated_dict = toolkit.get_action('user_update')(context, data_dict={'id' : user['id'], 'activity_streams_email_notifications' : True})
                    log.info('updated user: %s', user_updated_dict)
            except toolkit.ObjectNotFound:
                log.warn('Something went wrong!')
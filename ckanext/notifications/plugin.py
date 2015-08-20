# -*- coding: utf-8 -*-
import uuid
import logging
import datetime

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib.celery_app import celery
import ckan.logic as logic
from pylons import config


log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

def send_general_notification(context, data_dict):
    '''
    data_dict parameters:
        entity_id : <string>
        entity_type : <string>
        subject : <string>
        message : <string>
        recipients : <list> of pairs (email, display_name)
    '''
    user = toolkit.get_action('get_site_user')(
        {'model': model, 'ignore_auth': True, 'defer_commit': True}, {}
    )
    site_url = config.get('ckan.site_url')
    smtp_server = config.get('smtp.server', 'localhost:25')
    url = smtp_server.split(':')
    log.info('url: %s', url)
    if len(url)==2:
        smtp_server, smtp_server_port = url
        smtp_server_port = str(smtp_server_port)
    else:
        smtp_server_port = '25'
    log.info('smtp server: %s', smtp_server)
    log.info('smtp server port: %s', smtp_server_port) 
    mail_from = config.get('smtp.mail_from')
    mail_from_name = config.get('smtp.mail_from_name')
    context = {'site_url' : site_url,
                   'smtp_server' : smtp_server,
                   'smtp_server_port' : smtp_server_port,
                   'mail_from' : mail_from,
                   'mail_from_name' : mail_from_name}
    
    log.info('data for notification send: %s', data_dict)
    
    task_id = model.types.make_uuid()
    task_status = {
        'entity_id': data_dict['entity_id'],
        'entity_type': data_dict['entity_type'],
        'task_type': u'notify',
        'key': u'celery_task_id',
        'value': task_id,
        'error': u'',
        'last_updated': datetime.datetime.now().isoformat()
    }
    task_context = {
        'model': model,
        'user': user.get('name'),
    }
    toolkit.get_action('task_status_update')(task_context, task_status)
    celery.send_task('notifications.general.send', args=[context, data_dict], task_id=task_id)


class NotificationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IDomainObjectModification, inherit=True)
    plugins.implements(plugins.IResourceUrlChange)
    
    def get_actions(self):
        return {'send_general_notification' : send_general_notification}

    def configure(self, config):
        self.site_url = config.get('ckan.site_url')
        self.smtp_server = config.get('smtp.server', 'localhost:25')
        url = self.smtp_server.split(':')
        log.info('url: %s', url)
        if len(url)==2:
            smtp_server, smtp_server_port = url
            self.smtp_server = smtp_server
            self.smtp_server_port = str(smtp_server_port)
        else:
            self.smtp_server_port = '25'
        log.info('smtp server: %s', self.smtp_server)
        log.info('smtp server port: %s', self.smtp_server_port) 
        self.mail_from = config.get('smtp.mail_from')
        self.mail_from_name = config.get('smtp.mail_from_name')
    
    def notify(self, entity, operation=None):
        log.warn("notify")
        log.info('entity: %s', entity)
        log.info('operation: %s', operation)
        if not isinstance(entity, model.Resource) and not isinstance(entity, model.Package):
            return

        if operation:
                self._notify(entity, operation)
        else:
            # if operation is None, resource URL has been changed, as the
            # notify function in IResourceUrlChange only takes 1 parameter
            self._notify(entity, 'resource_url_changed')
    def _get_org_followers(self, org_id):
        if not org_id:
            return []
        context = {'ignore_auth' : True}
        followers = toolkit.get_action('group_follower_list')(context = context, data_dict={'id' : org_id})
        log.info('followers: %s', followers)
        users = []
        for follower in followers:
            user_obj = model.User.get(follower['id'])
            if user_obj:
                users.append((user_obj.email, user_obj.fullname))
        return users
    
    def _get_dataset_followers(self, dataset_id):
        context = {'ignore_auth' : True}
        followers = toolkit.get_action('dataset_follower_list')(context = context, data_dict={'id' : dataset_id})
        log.info('followers: %s', followers)
        users = []
        for follower in followers:
            user_obj = model.User.get(follower['id'])
            if user_obj:
                users.append((user_obj.email, user_obj.fullname))
        return users
        
    def _notify(self, entity, operation):
        user = toolkit.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True, 'defer_commit': True}, {}
        )
        log.info('entity: %s', entity)
        log.info('operation: %s', operation)
        data_dict = {}
        data_dict['recipients'] = []
        data_dict['entity_id'] = entity.id
        data_dict['entity_name'] = entity.name
        if isinstance(entity, model.Package):
            if operation=='new':
                data_dict['entity_action'] = u'vytvorený dataset'
            elif operation=='changed':
                data_dict['entity_action'] = u'upravený dataset'
            elif operation=='deleted':
                data_dict['entity_action'] = u'odstránený dataset'
            data_dict['private'] = entity.private
            if not data_dict['private']:
                data_dict['recipients'] = data_dict['recipients'] + \
                                         self._get_dataset_followers(entity.id) + \
                                         self._get_org_followers(entity.owner_org)
            data_dict['entity_type'] = 'package'
            data_dict['entity_url'] = toolkit.url_for(controller='package', action='read',id=entity.id)
            data_dict['entity_creator'] = entity.creator_user_id
            data_dict['entity_owner_org'] = entity.owner_org
            if entity.owner_org:
                owner_obj = model.User.get(entity.owner_org)
                if owner_obj:
                    data_dict['recipients'].append((owner_obj.email, owner_obj.fullname))
                else:
                    log.warn('couldnt find associated user object for organization %s', entity.owner_org)
        else:
            if operation=='new':
                data_dict['entity_action'] = u'vytvorený dátový zdroj'
            elif operation=='changed':
                data_dict['entity_action'] = u'upravený dátový zdroj'
            elif operation=='deleted':
                data_dict['entity_action'] = u'odstránený dátový zdroj'
            data_dict['entity_type'] = 'resource'
            data_dict['package_id'] = entity.resource_group.package.id
            data_dict['entity_url'] = toolkit.url_for(controller='package', action='resource_read',id=data_dict['package_id'], resource_id = entity.id)
            pkg = model.Package.get(data_dict['package_id'])
            data_dict['package_creator'] = pkg.creator_user_id
            data_dict['package_owner_org'] = pkg.owner_org
            pkg_owner_obj = model.User.get(pkg.owner_org)
            if pkg_owner_obj:
                data_dict['recipients'].append((pkg_owner_obj.email, pkg_owner_obj.fullname))
            else:
                log.warn('User account to org %s doesnt exist!')
            status = entity.extras.get('status', 'private')
            if status == 'private':
                data_dict['private'] = True
            else:
                data_dict['private'] = False
                data_dict['recipients'] =  data_dict['recipients'] + self._get_dataset_followers(data_dict['package_id']) + self._get_org_followers(data_dict['package_owner_org'])
        data_dict['revision_id'] = entity.revision_id
        #revision = model.Session.query(model.Revision).get(entity.revision_id)
        #executor_id = toolkit.get_converter('convert_user_name_or_id_to_id')(revision.author, {'session' : model.Session})
        #data_dict['executor_id'] = executor_id
        #executor_obj = model.User.get(executor_id)
        #data_dict['recipients'].append((executor_obj.email, executor_obj.fullname))
        log.info('data for notification send: %s', data_dict)
        
        task_id = model.types.make_uuid()
        task_status = {
            'entity_id': entity.id,
            'entity_type': data_dict['entity_type'],
            'task_type': u'notify',
            'key': u'celery_task_id',
            'value': task_id,
            'error': u'',
            'last_updated': datetime.datetime.now().isoformat()
        }
        task_context = {
            'model': model,
            'user': user.get('name'),
        }
        toolkit.get_action('task_status_update')(task_context, task_status)
        context = {'site_url' : self.site_url,
                   'smtp_server' : self.smtp_server,
                   'smtp_server_port' : self.smtp_server_port,
                   'mail_from' : self.mail_from,
                   'mail_from_name' : self.mail_from_name
        }
        celery.send_task('notifications.send', args=[context, data_dict], task_id=task_id)
        
        
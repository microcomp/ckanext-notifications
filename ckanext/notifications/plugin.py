import uuid
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib.celery_app import celery
import ckan.logic as logic
from suds.client import Client

log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

class NotificationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IDomainObjectModification, inherit=True)
    
    def get_actions(self):
        return {}
    
    def notify(self, entity, operation=None):
        log.warn("notify")
        self._notify(entity, operation)
    
    def notify_after_commit(self, entity, operation=None):
        log.warn("notify_after_commit")
        self._notify(entity, operation)
        
    def _notify(self, entity, operation):
        #model.Session.commit()
        if operation:
            log.warn("Operation")
            log.warn(operation)
            if operation == model.DomainObjectOperation.new and isinstance(entity, model.package.Package):
                log.warn("Dataset created")
                url = 'http://www.weather.gov/forecasts/xml/DWMLgen/wsdl/ndfdXML.wsd'
                client = Client(url)
                log.info('received wsdl: %s', client)
#                 log.warn(type(entity))
#                 log.warn(entity)
#                 
#                 try:
#                     following_users = toolkit.get_action('dataset_follower_list')(context={'ignore_auth': True},data_dict={'id' : entity.id})
#                 except: 
#                     log.warn("smth is wrong")
#                 log.warn(following_users)
#                 users = [u['id'] for u in following_users]
#                 log.warn(users)
#                 log.warn(entity.creator_user_id)
#                 if not entity.creator_user_id in users:
#                     log.warn("creator not following dataset")
#                     user_detail = toolkit.get_action('user_show')(data_dict={'id' : entity.creator_user_id})
#                     #logging.warn(user_detail)
#                     log.warn(user_detail['apikey'])
#                     #toolkit.get_action('follow_dataset')(context = {'ignore_auth': True, 'user':entity.creator_user_id}, data_dict={'id' : entity.id})
#                     #celery.send_task("notifications.followdataset", args=[user_detail['apikey'], entity.id], countdown=60, task_id=str(uuid.uuid4()))
#                     c = toolkit.c
#                     context = {'model': model, 'session': model.Session, 'user': c.user or c.author, 'auth_user_obj': c.userobj}
#                     data_dict = {'id': entity.id}
#                     try:
#                         toolkit.get_action('follow_dataset')(data_dict=data_dict)
#                     except ValidationError as e:
#                         log.error('Validation error occured when making attempt to follow dataset %s: %s', (entity.id,e))
#                     except NotAuthorized as e:
#                         log.error('Authorization error occured when making attempt to follow dataset %s: %s', (entity.id,e))
#                     log.warn("creator is following dataset since now!!!!")
#                 else:
#                     log.warn("User already following dataset")
            else:
                log.critical("Operation not defined")
        else:
            log.critical("Operation not defined")
            
        
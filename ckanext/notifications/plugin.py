# -*- coding: utf-8 -*-
import uuid
import logging
import datetime

from ckan.common import _, c, g
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
from ckan import model
from ckan.lib.celery_app import celery
import ckan.logic as logic
from pylons import config
from notification_db import notificationData_table, NotificationDB, notificationEmail_table, NotificationEmailDB

def get_follow_settings(user_id):
    search = {'user_id': user_id}
    results = NotificationDB.get(**search)    
    return results

def admin_get_user_followings_auth(context, data_dict=None):    
    return admin_dashboard_notifications_auth(context,data_dict)
    
def admin_dashboard_notifications_auth(context,data_dict=None):    
    user_roles = toolkit.get_action('user_custom_roles')(context, data_dict)
    if 'MOD-R-DATA' in user_roles:
        return {'success': True}
    return {'success': False, 'msg': _('Only data curator is authorized to manage notification settings.')}

@logic.side_effect_free
def admin_get_user_followings(context,data_dict):
    logic.check_access('admin_dashboard_notifications',context)
    user = data_dict['user']
    followed = toolkit.get_action('followee_list')(data_dict={'id' : user},context={'ignore_auth': True})
    followSettings = get_follow_settings(user)        
    for rf in followSettings:
        if rf.type == "resource":
            dictData = toolkit.get_action('resource_show')(data_dict={'id':rf.entity_id},context={'ignore_auth': True})               
            followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData})
    
    count = 0
    for fo in followed:
        fo["count"] = count
        fo["active"] = True
        for fs in followSettings:
            if fs.entity_id == fo["dict"]["id"]:
                fo["active"] = fs.active
                break
        count += 1
    ret = {}
    ret['followed_datasets'] = list(filter(lambda x: x["type"] == "dataset",followed))
    ret['followed_orgs'] = list(filter(lambda x: x["type"] == "organization",followed))
    ret['followed_resources'] = list(filter(lambda x: x["type"] == "resource",followed))
    ret['followed_count'] = count
    return ret

def get_notif_email(user_id):
    search = {'user_id': user_id}
    results = NotificationEmailDB.get(**search)
    if results is None or len(results) == 0:
        return None
    else:
        return results[0]
        
def get_dataset_followers_active(dataset_id):
    search = {'entity_id': dataset_id, 'type':'dataset', 'active':True}
    results = NotificationDB.get(**search)
    
    context = {'ignore_auth':True}    
    
    dsFollowers = toolkit.get_action('dataset_follower_list')(context = context, data_dict={'id' : dataset_id})
    users = []
    for follower in results:
        df = None
        for dsfol in dsFollowers:
            if dsfol["id"] == follower.user_id:
                df = dsfol
                break
        if df is None:
            NotificationDB.deleteModel(follower)
            continue
        user_obj = model.User.get(follower.user_id)
        email_obj = get_notif_email(follower.user_id)
        if user_obj and email_obj:
            users.append((email_obj.email, user_obj.fullname,'dataset'))
    return users

def get_org_followers_active(org_id):
    search = {'entity_id': org_id, 'type':'organization', 'active':True}
    results = NotificationDB.get(**search)
    users = []
    context = {'ignore_auth':True}    
    orgFollowers = toolkit.get_action('group_follower_list')(context = context, data_dict={'id' : org_id})
    for follower in results:
        of = None
        for orgfol in orgFollowers:
            if orgfol["id"] == follower.user_id:
                of = orgfol
                break
        if of is None:
            NotificationDB.deleteModel(follower)
            continue
        user_obj = model.User.get(follower.user_id)
        email_obj = get_notif_email(follower.user_id)
        if user_obj and email_obj:
            users.append((email_obj.email, user_obj.fullname,'organization'))
    return users

def get_resource_followers_active(resource_id):
    search = {'entity_id': resource_id, 'type':'resource', 'active':True}
    results = NotificationDB.get(**search)
    users = []
    for follower in results:
        user_obj = model.User.get(follower.user_id)
        email_obj = get_notif_email(follower.user_id)
        if user_obj and email_obj:
            users.append((email_obj.email, user_obj.fullname,'resource'))
    return users

log = logging.getLogger(__name__)

NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

def follow_resource(context, data_dict):
    search = {'user_id': context["user"],'type':'resource','entity_id':data_dict['id']}
    results = NotificationDB.get(**search)
    if results is None or len(results) == 0:
        dbEntry = NotificationDB(user_id = context["user"], entity_id=data_dict['id'],active=True,type="resource")
    else:
        dbEntry = results[0]
    dbEntry.active = True
    dbEntry.save()

def unfollow_resource(context, data_dict):
    search = {'user_id': context["user"],'type':'resource','entity_id':data_dict['id']}
    results = NotificationDB.get(**search)
    
    if results and len(results) > 0:
        NotificationDB.deleteModel(results[0])

def admin_follow_resource(context, data_dict):
    logic.check_access('admin_dashboard_notifications',context)
    search = {'user_id': data_dict["user"],'type':'resource','entity_id':data_dict['id']}
    results = NotificationDB.get(**search)
    if results is None or len(results) == 0:
        dbEntry = NotificationDB(user_id = data_dict["user"], entity_id=data_dict['id'],active=True,type="resource")
    else:
        dbEntry = results[0]
    dbEntry.active = True
    dbEntry.save()
    
def admin_follow_org(context, data_dict):
    logic.check_access('admin_dashboard_notifications',context)
    dictData = toolkit.get_action("organization_show")(data_dict={'id':data_dict["name"]})                
    toolkit.get_action('follow_group')(data_dict={'id' : dictData["id"]},context={'ignore_auth':True,'user':data_dict["selUser"]})
    return {'success':True}
    
def admin_follow_dataset(context, data_dict):
    logic.check_access('admin_dashboard_notifications',context)
    dictData = toolkit.get_action("package_show")(data_dict={'id':data_dict["name"]})                
    toolkit.get_action('follow_dataset')(data_dict={'id' : dictData["id"]},context={'ignore_auth':True,'user':data_dict["selUser"]})
    return {'success':True}

def admin_unfollow_resource(context, data_dict):
    logic.check_access('admin_dashboard_notifications',context)
    search = {'user_id': data_dict["user"],'type':'resource','entity_id':data_dict['id']}
    results = NotificationDB.get(**search)
    
    if results and len(results) > 0:
        NotificationDB.deleteModel(results[0])

def get_res_follower_list(context, data_dict):
    search = {'user_id': context["user"],'type':'resource'}
    results = NotificationDB.get(**search)
    return results

def am_following_res(context, data_dict):
    search = {'user_id': context['user'],'type':'resource','entity_id':data_dict['id']}
    results = NotificationDB.get(**search)
    return results and len(results) > 0

def check_notification_email(context, data_dict):

    notifEmail = get_notif_email(context["user"])
    if notifEmail is None:
        return False
    else:
        return True

def notification_administration():
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               'for_view': True}
    try:
        logic.check_access('admin_dashboard_notifications', context)
        return True
    except logic.NotAuthorized:
        return False
    return False
        
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
    log.info('send_general_notification')
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

def notify_package_create(context,data_dict):
    if "defer_commit" in context and context["defer_commit"]:
        return

    NotificationPlugin.plugRef._notify(context["package"],"new")            
    
def notify_package_update(context,data_dict):
    if "defer_commit" in context and context["defer_commit"]:
        return

    NotificationPlugin.plugRef._notify(context["package"],"changed")
    
def notify_resource_create(context,data_dict):
    if "defer_commit" in context and context["defer_commit"]:
        return

    NotificationPlugin.plugRef._notify(context["resource"],"new")
    
def notify_resource_update(context,data_dict):
    if "defer_commit" in context and context["defer_commit"]:
        return    
    NotificationPlugin.plugRef._notify(context["resource"],"changed")
    

class NotificationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDomainObjectModification, inherit=True)
    plugins.implements(plugins.IResourceUrlChange)
    plugins.implements(plugins.IMapper, inherit=True)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers, inherit=False)
    
    plugRef = None
    
    def get_helpers(self):
        return {'notification_administration' : notification_administration}
    
    def get_auth_functions(self):
        return {'admin_get_user_followings':admin_get_user_followings_auth,
                'admin_dashboard_notifications':admin_dashboard_notifications_auth
        }
    
    def before_map(self, m):
        m.connect(
            'user_dashboard_notifications', #name of path route
            '/dashboard/notifications', #url to map path to
            controller='ckanext.notifications.controller:NotificationsController', #controller
            action='UserNotifications') #controller action (method)
        m.connect(
            'user_dashboard_notifications_savechanges', #name of path route
            '/dashboard/notifications/saveChanges', #url to map path to
            controller='ckanext.notifications.controller:NotificationsController', #controller
            action='SaveChanges') #controller action (method)
        m.connect(
            'admin_dashboard_notifications', #name of path route
            '/admin/notifications', #url to map path to
            controller='ckanext.notifications.admin_controller:AdminNotificationsController', #controller
            action='AdminNotifications') #controller action (method)
        m.connect(
            'admin_dashboard_notifications_savechanges', #name of path route
            '/admin/notifications/saveChanges', #url to map path to
            controller='ckanext.notifications.admin_controller:AdminNotificationsController', #controller
            action='SaveChanges') #controller action (method)
        m.connect(
            'user_dashboard_notifications_page', #name of path route
            '/dashboard/notifications/notifications_page', #url to map path to
            controller='ckanext.notifications.controller:NotificationsController', #controller
            action='NotificationsPage') #controller action (method)
        m.connect(
            'admin_dashboard_notifications_page', #name of path route
            '/admin/notifications/notifications_page', #url to map path to
            controller='ckanext.notifications.admin_controller:AdminNotificationsController', #controller
            action='NotificationsPage') #controller action (method)
        return m
    
    def get_actions(self):
        return {'send_general_notification' : send_general_notification,
        'check_notification_email' : check_notification_email,
        'follow_resource':follow_resource,
        'unfollow_resource':unfollow_resource,
        'get_res_follower_list':get_res_follower_list,
        'am_following_resource': am_following_res,
        'admin_follow_resource':admin_follow_resource,
        'admin_unfollow_resource':admin_unfollow_resource,
        'admin_get_user_followings':admin_get_user_followings,
        'admin_follow_org':admin_follow_org,
        'admin_follow_dataset':admin_follow_dataset,
        'notify_package_create' : notify_package_create,
        'notify_package_update' : notify_package_update,
        'notify_resource_create' : notify_resource_create,
        'notify_resource_update' : notify_resource_update
        }
    
    def after_insert(self, mapper, connection, instance):
        log.info('-------------------------')
        log.info('mapper: %s', mapper)
        log.info('connection: %s', connection)
        log.info('instance: %s', instance)
        
    def after_update(self, mapper, connection, instance):
        log.info('-------------------------')
        log.info('mapper: %s', mapper)
        log.info('connection: %s', connection)
        log.info('instance: %s', instance)
    
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
        if not notificationData_table.exists():
            notificationData_table.create()
        if not notificationEmail_table.exists():
            notificationEmail_table.create()      
        NotificationPlugin.plugRef = self
        
    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')       
    
    def notify(self, entity, operation=None):        
        if not isinstance(entity, model.Resource) and not isinstance(entity, model.Package):
            return

        if operation=="deleted":                
                self._notify(entity, operation)
        else:
            return
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
        
        log.warn("notify")
        log.info('entity: %s', entity)
        log.info('operation: %s', operation)                               
        
        data_dict = {}
        data_dict['recipients'] = []
        data_dict['entity_id'] = entity.id
        data_dict['entity_name'] = entity.name
        if isinstance(entity, model.Package):
            if operation=='new':
                data_dict['entity_action'] = u'vytvorený dataset'
            elif operation=='resource_url_changed':                
                data_dict['entity_action'] = u'upravený dataset'                
            elif operation=='deleted':
                data_dict['entity_action'] = u'odstránený dataset'
            elif operation=='changed':
                data_dict['entity_action'] = u'upravený dataset'                
            data_dict['private'] = entity.private
            if not data_dict['private']:
                data_dict['recipients'] = data_dict['recipients'] + \
                                         get_dataset_followers_active(entity.id) + \
                                         get_org_followers_active(entity.owner_org)
            data_dict['entity_type'] = 'package'
            data_dict['entity_url'] = toolkit.url_for(controller='package', action='read',id=entity.id)
            data_dict['entity_creator'] = entity.creator_user_id
            data_dict['entity_owner_org'] = entity.owner_org
            if entity.owner_org:
                owner_obj = model.User.get(entity.owner_org)
                #if owner_obj:
                #    data_dict['recipients'].append((owner_obj.email, owner_obj.fullname))
                #else:
                #    log.warn('couldnt find associated user object for organization %s', entity.owner_org)
        else:
            if operation=='new':
                data_dict['entity_action'] = u'vytvorený dátový zdroj'
            elif operation=='resource_url_changed':                
                data_dict['entity_action'] = u'upravený dátový zdroj'                
            elif operation=='deleted':
                data_dict['entity_action'] = u'odstránený dátový zdroj'
            elif operation=='changed':
                data_dict['entity_action'] = u'upravený dátový zdroj'                
            
            data_dict['entity_type'] = 'resource'
            data_dict['package_id'] = entity.resource_group.package.id
            data_dict['entity_url'] = toolkit.url_for(controller='package', action='resource_read',id=data_dict['package_id'], resource_id = entity.id)
            pkg = model.Package.get(data_dict['package_id'])
            data_dict['package_creator'] = pkg.creator_user_id
            data_dict['package_owner_org'] = pkg.owner_org
            pkg_owner_obj = model.User.get(pkg.owner_org)
            #if pkg_owner_obj:
            #    data_dict['recipients'].append((pkg_owner_obj.email, pkg_owner_obj.fullname))
            #else:
            #    log.warn('User account to org %s doesnt exist!')
            status = entity.extras.get('status', 'private')
            if status == 'private':
                data_dict['private'] = True
            else:
                data_dict['private'] = False
                data_dict['recipients'] =  data_dict['recipients'] + get_resource_followers_active(entity.id) + get_dataset_followers_active(data_dict['package_id']) + get_org_followers_active(data_dict['package_owner_org'])
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
        #NotificationTimes.commit()
        
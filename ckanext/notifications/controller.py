import ckan.plugins as p
import ckan.lib.base as base
import ckan.plugins.toolkit as toolkit
from ckan.common import _, c, g
import re

from notification_db import notificationData_table, NotificationDB, notificationEmail_table, NotificationEmailDB

def get_notif_email(user_id):
    search = {'user_id': user_id}
    results = NotificationEmailDB.get(**search)
    if results is None or len(results) == 0:
        return None
    else:
        return results[0]

def get_follow_settings(user_id):
    search = {'user_id': user_id}
    results = NotificationDB.get(**search)    
    return results

def set_active(user_id,entity_id,active):
    search = {'user_id': user_id,'entity_id': entity_id}
    results = NotificationDB.get(**search)    
    results[0].active = active
    results[0].save()
    return results

class NotificationsController(base.BaseController):
    def UserNotifications(self):
    
        if c.userobj is None:
            base.redirect_to(controller="user", action="login")
        followed = toolkit.get_action('followee_list')(data_dict={'id' : c.user})
        
        fId = toolkit.request.params["fId"] if "fId" in toolkit.request.params else None
        fType = toolkit.request.params["fType"] if "fType" in toolkit.request.params else None
        
        if fId and fType:
            if fType == "dataset":
                dictData = toolkit.get_action('package_show')(data_dict={'id':fId})
                followed.append({"display_name": dictData["title"],"type":fType,"dict":dictData})
            elif fType == "organization":
                dictData = toolkit.get_action('organization_show')(data_dict={'id':fId})                
                followed.append({"display_name": dictData["title"],"type":fType,"dict":dictData})
                fId = dictData["id"]
            elif fType == "resource":
                dictData = toolkit.get_action('resource_show')(data_dict={'id':fId})                
                followed.append({"display_name": dictData["name"],"type":fType,"dict":dictData})        
        
        followSettings = get_follow_settings(c.user)        
        for rf in followSettings:
            if rf.type == "resource":
                dictData = toolkit.get_action('resource_show')(data_dict={'id':rf.entity_id})
                revisionData = toolkit.get_action('revision_show')(data_dict={'id':dictData["revision_id"]})
                if revisionData and revisionData["packages"] and len(revisionData["packages"]) > 0:
                    packageData = toolkit.get_action('package_show')(data_dict={'id':revisionData["packages"][0]})
                    if packageData:
                        followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData, "package_data":packageData})
                    else:
                        followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData, "package_data":None})
                else:
                    followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData, "package_data":None})
            
        count = 0
        for fo in followed:
            fo["count"] = count
            fo["active"] = True
            for fs in followSettings:
                if fs.entity_id == fo["dict"]["id"]:
                    fo["active"] = fs.active
                    break
            count += 1        
        
        c.followed_datasets = list(filter(lambda x: x["type"] == "dataset",followed))
        c.followed_orgs = list(filter(lambda x: x["type"] == "organization",followed))
        c.followed_resources = list(filter(lambda x: x["type"] == "resource",followed))
        c.ret_url = toolkit.request.params["ret_url"] if "ret_url" in toolkit.request.params else None
        c.fId = fId
        c.fType = fType
        
        c.followed_count = count       
        if "emailError" in toolkit.request.params:
            c.email_error = _('Invalid Email')
        else:
            c.email_error = None
        dbMail = get_notif_email(c.user)
        if not dbMail is None:
            c.notification_email = dbMail.email
        return base.render('user/dashboard_notifications.html')
    def SaveChanges(self):      
        p = toolkit.request.params
        foeCount = int(p["foeCount"])
        followSettings = get_follow_settings(c.user)
        userId = c.user
        notifEmail = p["email"]
        emailMatch = re.search("^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",notifEmail)
        if emailMatch is None and not notifEmail is None and notifEmail != "" or len(notifEmail) > 255:        
            return base.redirect_to(controller='ckanext.notifications.controller:NotificationsController',action='UserNotifications',emailError=True, fId = p["fId"] if "fId" in p else None,fType = p["fType"] if "fType" in p else None,ret_url = p["ret_url"] if "ret_url" in p else None )        
        
        if notifEmail is None or notifEmail == "":
            delet = {'user_id' : userId}
            NotificationEmailDB.delete(**delet)
            
        else:
            dbNotifEmail = get_notif_email(c.user)
            if dbNotifEmail is None:
                dbNotifEmail = NotificationEmailDB(userId,notifEmail)
            dbNotifEmail.email = notifEmail
            dbNotifEmail.save()
        
        NotificationEmailDB.commit()
        
        for i in range(foeCount):
            if "foe[{}].id".format(i) not in p:
                continue
            entityId = p["foe[{}].id".format(i)]
            type = p["foe[{}].type".format(i)]
            dbFs = None
            for fs in followSettings:
                if fs.type == type and fs.entity_id == entityId:
                    dbFs = fs
                    break
            
            if "foe[{}].delete".format(i) in p and not ("fId" in p and p["fId"] == entityId):
                if type == "organization":
                    toolkit.get_action('unfollow_group')(data_dict={'id' : entityId})
                    if dbFs:
                        NotificationDB.deleteModel(dbFs)
                elif type == "dataset":
                    toolkit.get_action('unfollow_dataset')(data_dict={'id' : entityId})
                    if dbFs:
                        NotificationDB.deleteModel(dbFs)
                elif type == "resource":
                    if dbFs:
                        NotificationDB.deleteModel(dbFs)
                
            else:
                if dbFs is None:
                    dbFs = NotificationDB(entityId,userId,True,type)
                dbFs.active = "foe[{}].active".format(i) in p
                dbFs.save()
                
        
        if "fId" in p and not notifEmail is None and notifEmail != "":
            fId = p["fId"]
            fType = p["fType"]
            if fType == "organization":
                toolkit.get_action('follow_group')(data_dict={'id' : fId})
            elif fType == "dataset":
                toolkit.get_action('follow_dataset')(data_dict={'id' : fId})
            elif fType == "resource":
                toolkit.get_action('follow_resource')(context={'user':c.user},data_dict={'id' : fId})
            NotificationDB.commit()
            if "ret_url" in p:            
                if p["fType"] == "dataset":
                    return toolkit.redirect_to(controller="package", action="read", id=fId)
                elif p["fType"] == "organization":
                    return toolkit.redirect_to(controller="organization", action="read", id=fId)
                elif p["fType"] == "resource":
                    return toolkit.redirect_to(controller="package", action="resource_read", id=fId)
        else:
            NotificationDB.commit()
        return base.redirect_to('user_dashboard_notifications')
        
    def follow(self):
        toolkit.get_action("follow_resource")(data_dict={'user':c.user,'id':toolkit.request.params['id']})
        
    def unfollow(self):
        toolkit.get_action("unfollow_resource")(data_dict={'user':c.user,'id':toolkit.request.params['id']})
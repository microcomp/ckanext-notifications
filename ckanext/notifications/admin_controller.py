import math
import re
import ckan.model as model
import ckan.plugins as p
import ckan.lib.base as base
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
from ckan.common import _, c, g
import ckan.lib.helpers as helpers

from notification_db import notificationData_table, NotificationDB, notificationEmail_table, NotificationEmailDB

def get_dataset_followers(dataset_id):
    search = {'entity_id': dataset_id, 'type':'dataset'}
    results = NotificationDB.get(**search)
    context = {}
    context["ignore_auth"] = True
    dsFollowers = toolkit.get_action('dataset_follower_list')(context = context, data_dict={'id' : dataset_id})
    users = []
    count = 0
    for fol in dsFollowers:
        foundRes = None
        for res in results:
            if res.user_id == fol["id"]:
                foundRes = res                
                break;        
        users.append({'user_obj':fol,'notif_info': foundRes,'count':count})
        count += 1      
    return (users,count)

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
    if results is None or len(results) == 0:
        results = NotificationDB(entityId,userId,active,'')
    else:
        results = results[0]
    results.active = active
    results.save()
    return results

class AdminNotificationsController(base.BaseController):
    def AdminNotifications(self):
        context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
        logic.check_access('admin_dashboard_notifications',context)
        c.uao = c.userobj
        p = toolkit.request.params
        c.users = toolkit.get_action('user_list')(data_dict={},context={})
        c.datasets = toolkit.get_action('package_list')(data_dict={},context={})
        c.organizations = toolkit.get_action('organization_list')(data_dict={},context={})
        if "users" in p:
            selUser = p["users"]
            c.selUser = selUser
            
            followed = toolkit.get_action('followee_list')(data_dict={'id' : selUser},context={'ignore_auth':True})
            followSettings = get_follow_settings(selUser)        
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
            
            c.followed_datasets = list(filter(lambda x: x["type"] == "dataset",followed))
            c.followed_datasets.sort(key=lambda x: helpers.stripDiacritic(x["dict"]["title"].lower()))
            c.followed_datasets_count = len(c.followed_datasets)
            c.followed_datasets_pages = int(math.ceil( float(c.followed_datasets_count)/float(10)))
            c.followed_datasets = c.followed_datasets[0:10]
            c.followed_orgs = list(filter(lambda x: x["type"] == "organization",followed))
            c.followed_orgs.sort(key=lambda x: helpers.stripDiacritic(x["display_name"].lower()))
            c.followed_orgs_count = len(c.followed_orgs)
            c.followed_orgs_pages = int(math.ceil( float(c.followed_orgs_count)/float(10)))
            c.followed_orgs = c.followed_orgs[0:10]
            c.followed_resources = list(filter(lambda x: x["type"] == "resource",followed))
            c.followed_resources.sort(key=lambda x: helpers.stripDiacritic((x["package_data"]['title'] + "/" + x["dict"]["name"]).lower()))
            c.followed_resources_count = len(c.followed_resources)
            c.followed_resources_pages = int(math.ceil( float(c.followed_resources_count)/float(10)))
            c.followed_resources = c.followed_resources[0:10]
            c.ret_url = toolkit.request.params["ret_url"] if "ret_url" in toolkit.request.params else None
            
            c.followed_datasets_start_count = count
            for fo in c.followed_datasets:
                fo["count"] = count
                fo["active"] = True
                for fs in followSettings:
                    if fs.entity_id == fo["dict"]["id"]:
                        fo["active"] = fs.active
                        break
                count += 1
            c.followed_orgs_start_count = count
            for fo in c.followed_orgs:
                fo["count"] = count
                fo["active"] = True
                for fs in followSettings:
                    if fs.entity_id == fo["dict"]["id"]:
                        fo["active"] = fs.active
                        break
                count += 1
            c.followed_resources_start_count = count
            for fo in c.followed_resources:
                fo["count"] = count
                fo["active"] = True
                for fs in followSettings:
                    if fs.entity_id == fo["dict"]["id"]:
                        fo["active"] = fs.active
                    break
            count += 1
            
            c.followed_count = count       
            if "emailError" in toolkit.request.params:
                c.email_error = _('Invalid Email')
            else:
                c.email_error = None
            dbMail = get_notif_email(selUser)
            if not dbMail is None:
                c.notification_email = dbMail.email
                
        elif "datasets" in p:
           
            ds = toolkit.get_action('package_show')(data_dict={'id':p["datasets"]},context=context)
            c.selDatasetId = ds["id"]
            c.selDatasetName = p["datasets"]
            search = {'entity_id': c.selDatasetId, 'type':'dataset'}
            results = NotificationDB.get(**search)
            c.results = results
            dsFollowers = toolkit.get_action('dataset_follower_list')(context = context, data_dict={'id' : c.selDatasetId})
            users = []
            count = 0
            for fol in dsFollowers:
                foundRes = None
                for res in results:
                    if res.user_id == fol["id"]:
                        foundRes = res                
                        break;
                notifEmail = get_notif_email(fol["id"])
                users.append({'user_obj':fol,'notif_info': foundRes,'count':count,'email':notifEmail.email if notifEmail else None})
                count += 1     
            
            
            c.datasetFollowers = users
            c.fcount = count
        
        return base.render('admin/admin_notifications.html')
        
    def SaveChanges(self):
        context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
        logic.check_access('admin_dashboard_notifications',context)
        p = toolkit.request.params        
        if p["saveType"] == "user":            
            selUser = p["selUser"]
            foeCount = int(p["foeCount"])
            user_obj = toolkit.get_action('user_show')(data_dict={'id' : selUser})
            followSettings = get_follow_settings(selUser)
            userId = selUser
            notifEmail = p["email"]
            emailMatch = re.search("^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",notifEmail)
            if emailMatch is None and not notifEmail is None and notifEmail != "":        
                return base.redirect_to(controller='ckanext.notifications.admin_controller:AdminNotificationsController',action='AdminNotifications',emailError=True, fId = p["fId"] if "fId" in p else None,fType = p["fType"] if "fType" in p else None,ret_url = p["ret_url"] if "ret_url" in p else None,users = selUser )        
            
            if notifEmail is None or notifEmail == "":
                delet = {'user_id' : userId}
                NotificationEmailDB.delete(**delet)
                
            else:
                dbNotifEmail = get_notif_email(userId)
                if dbNotifEmail is None:
                    dbNotifEmail = NotificationEmailDB(userId,notifEmail)
                dbNotifEmail.email = notifEmail
                dbNotifEmail.save()
            
            NotificationEmailDB.commit()
            
            for key in p:
                matchObj = re.match(r'foe\[(\d+)\]\.id',key, re.I)
            
                if not matchObj:
                    continue
                id = matchObj.groups(1)[0]
                entityId = p["foe[{}].id".format(id)]
                type = p["foe[{}].type".format(id)]
                dbFs = None
                for fs in followSettings:
                    if fs.type == type and fs.entity_id == entityId:
                        dbFs = fs
                        break
                
                if "foe[{}].delete".format(id) in p and not ("fId" in p and p["fId"] == entityId):
                    if type == "organization":
                        toolkit.get_action('unfollow_group')(data_dict={'id' : entityId},context={'ignore_auth':True,'user':selUser,'user_obj':user_obj})
                        if dbFs:
                            NotificationDB.deleteModel(dbFs)
                    elif type == "dataset":
                        toolkit.get_action('unfollow_dataset')(data_dict={'id' : entityId},context={'ignore_auth':True,'user':selUser,'user_obj':user_obj})
                        if dbFs:
                            NotificationDB.deleteModel(dbFs)
                    elif type == "resource":
                        if dbFs:
                            NotificationDB.deleteModel(dbFs)
                    
                else:
                    if dbFs is None:
                        dbFs = NotificationDB(entityId,userId,True,type)
                    dbFs.active = "foe[{}].active".format(id) in p
                    dbFs.save()
                    
            
            if "fId" in p and not notifEmail is None and notifEmail != "":
                fId = p["fId"]
                fType = p["fType"]
                if fType == "organization":
                    toolkit.get_action('follow_group')(data_dict={'id' : fId},context={'ignore_auth':True,'user':selUser,'user_obj':user_obj})
                elif fType == "dataset":
                    toolkit.get_action('follow_dataset')(data_dict={'id' : fId},context={'ignore_auth':True,'user':selUser,'user_obj':user_obj})
                elif fType == "resource":
                    toolkit.get_action('follow_resource')(context={'user':selUser,'ignore_auth':True},data_dict={'id' : fId})
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
            return base.redirect_to(controller='ckanext.notifications.admin_controller:AdminNotificationsController',action='AdminNotifications',users=selUser)
        if p["saveType"] == "dataset":
            foeCount = int(p["foeCount"])
            selDatasetName = p["selDatasetName"]
            selDatasetId = p["selDatasetId"]
            for i in range(foeCount):
                if "foe[{}].id".format(i) not in p:
                    continue
                userId = p["foe[{}].id".format(i)]
                
                dbNotifEmail = get_notif_email(c.user)
                notifEmail = p["foe[{}].notifEmail".format(i)]
                userFs = get_follow_settings(userId)
                if notifEmail is None or notifEmail == "":
                    delet = {'user_id' : userId}
                    NotificationEmailDB.delete(**delet)
                else:
                    if dbNotifEmail is None:
                        dbNotifEmail = NotificationEmailDB(userId,notifEmail)
                    dbNotifEmail.email = notifEmail
                    dbNotifEmail.save()
                
                if "foe[{}].delete".format(i) in p:
                    toolkit.get_action('unfollow_dataset')(data_dict={'id' : entityId},context={'ignore_auth':True,'user':selUser,'user_obj':user_obj})
                    for fs in userFs:
                        if fs.entity_id == selDatasetId:
                            NotificationDB.deleteModel(fs)
                            break
                else:
                    dbFs = None
                    for fs in userFs:
                        if fs.entity_id == selDatasetId:
                            dbFs = fs
                            break
                    if dbFs is None:
                        dbFs = NotificationDB(entityId,userId,True,'dataset')
                    dbFs.active = "foe[{}].active".format(i) in p
                    dbFs.save()
                    
            return base.redirect_to(controller='ckanext.notifications.admin_controller:AdminNotificationsController',action='AdminNotifications',datasets=selDatasetName)

    def NotificationsPage(self):
        context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj}
        logic.check_access('admin_dashboard_notifications',context)
        c.uao = c.userobj
        p = toolkit.request.params
        selUser = p["selUser"]
        requestedPage = int(p["page"]) - 1
        pageType = p["type"]
        c.requestedPage = requestedPage
        c.pageType = pageType
        startCount = int(p["startCount"])
        followSettings = get_follow_settings(c.user)
        
        
        if "organization" in pageType:
            followed = toolkit.get_action('followee_list')(data_dict={'id' : selUser},context={'ignore_auth':True})
            c.followed = list(filter(lambda x: x["type"] == "organization",followed))
            c.followed.sort(key=lambda x: helpers.stripDiacritic(x["display_name"].lower()))            
            c.followed = c.followed[(requestedPage*10):(((requestedPage+1)*10))]
            
            for fo in c.followed:
                fo["url"] = "/organization/" + fo["dict"]["name"]
        elif "resource" in pageType:
            followed = []
            
            for rf in followSettings:
                if rf.type == "resource":                    
                    dictData = toolkit.get_action('resource_show')(data_dict={'id':rf.entity_id})
                    revisionData = toolkit.get_action('revision_show')(data_dict={'id':dictData["revision_id"]})
                    if revisionData and revisionData["packages"] and len(revisionData["packages"]) > 0:
                        packageData = toolkit.get_action('package_show')(data_dict={'id':revisionData["packages"][0]})
                        if packageData:                            
                            followed.append({"display_name":  packageData['title'] + "/" + dictData["name"] ,"type":"resource","dict":dictData, "package_data":packageData,"url":"/dataset/" + packageData['name'] + "/resource/" + dictData["id"]})
                        else:
                            followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData, "package_data":None})
                    else:
                        followed.append({"display_name":  dictData["name"] ,"type":"resource","dict":dictData, "package_data":None})
            
            followed.sort(key=lambda x: helpers.stripDiacritic(x["display_name"].lower()))            
            followed = followed[(requestedPage*10):(((requestedPage+1)*10))]
            
            c.followed = followed
        elif "dataset" in pageType:
            followed = toolkit.get_action('followee_list')(data_dict={'id' : selUser},context={'ignore_auth':True})
            c.followed = list(filter(lambda x: x["type"] == "dataset",followed))
            c.followed.sort(key=lambda x: helpers.stripDiacritic(x["dict"]["title"].lower()))            
            c.followed = c.followed[(requestedPage*10):(((requestedPage+1)*10))]
            for fo in c.followed:
                fo["url"] = "/dataset/" + fo["dict"]["name"]
                fo["display_name"] = fo["dict"]["title"]
                
        for fo in c.followed:
            fo["count"] = startCount
            fo["active"] = True
            for fs in followSettings:
                if fs.entity_id == fo["dict"]["id"]:
                    fo["active"] = fs.active
                    break
            startCount += 1
        
        return base.render('user/notifications_page.html')
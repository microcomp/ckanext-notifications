
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import uuid
from ckan import model
from ckan.lib.celery_app import celery
from ckan.lib.celery_app import celery
import logging
@celery.task(name = "notifications.followdataset")
def followdataset(user_id, dataset_id):
    logging.warn("follow")
    toolkit.get_action('follow_dataset')(context = {'user' : user_id, 'model' : model, 'session' : model.Session}, data_dict={'id' : dataset_id}) 


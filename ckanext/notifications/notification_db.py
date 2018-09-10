import uuid
import logging

from ckan.model import domain_object
from ckan.model.meta import metadata, Session, mapper
from sqlalchemy import types, Column, Table, UniqueConstraint

log = logging.getLogger(__name__)

def make_uuid():
    return unicode(uuid.uuid4())

class NotificationDB(domain_object.DomainObject):
    def __init__(self, entity_id, user_id, active,type):        
        self.entity_id = entity_id
        self.user_id = user_id
        self.active = active
        self.type = type
        
    @classmethod
    def get(cls, **kw):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()
    @classmethod
    def delete(cls, **kw):
        query = Session.query(cls).autoflush(False).filter_by(**kw).all()
        for i in query:
            Session.delete(i)
        Session.commit()
        return
    @classmethod
    def deleteModel(cls, m):
        Session.delete(m)
        Session.commit()
        return
    @classmethod
    def commit(cls):
        Session.commit()

class NotificationEmailDB(domain_object.DomainObject):
    def __init__(self, user_id, email):
        self.user_id = user_id
        self.email = email
    @classmethod
    def get(cls, **kw):
        '''Finds a single entity in the register.'''
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kw).all()
    @classmethod
    def delete(cls, **kw):
        query = Session.query(cls).autoflush(False).filter_by(**kw).all()
        for i in query:
            Session.delete(i)
        Session.commit()
        return
    @classmethod
    def deleteModel(cls, m):        
        Session.delete(m)
        Session.commit()
        return
    @classmethod
    def commit(cls):
        Session.commit()

notificationData_table = Table('notification_data', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('entity_id', types.UnicodeText, default=u'', nullable=False),
        Column('user_id', types.UnicodeText, default=u'', nullable=False),
        Column('active', types.Boolean, default=u'', nullable=False),
        Column('type', types.UnicodeText, default=u'', nullable=False),
    )

mapper(NotificationDB, notificationData_table)

notificationEmail_table = Table('notification_email', metadata,
        Column('user_id', types.UnicodeText, default=u'', nullable=False,primary_key=True),
        Column('email', types.UnicodeText, default=u'', nullable=False,primary_key=True)
    )

mapper(NotificationEmailDB, notificationEmail_table)
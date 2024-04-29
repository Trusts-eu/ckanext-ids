import logging
import datetime

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import types
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import relation

from ckan.model.meta import metadata, mapper, Session
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = [
    'IdsAgreement', 'ids_agreement_table',
    'IdsResource', 'ids_resource_table',
    'IdsSubscription', 'ids_subscription_table',
    'WorkflowExecution', 'dbx_workflow_execution_table'
]

ids_agreement_table = None
ids_resource_table = None
ids_subscription_table = None
dbx_workflow_execution_table = None


def setup():
    if ids_subscription_table is None:
        define_ids_tables()
        log.debug('IDS tables defined in memory')

    if dbx_workflow_execution_table is None:
        define_ids_tables()
        log.debug('DBX tables defined in memory')

    if not ids_agreement_table.exists():

        # Create each table individually rather than
        # using metadata.create_all()
        ids_resource_table.create()
        ids_agreement_table.create()
        ids_subscription_table.create()
        log.debug("IDS tables created")
    elif not ids_subscription_table.exists():
        ids_subscription_table.create()
        log.debug("IDS subscription table added.")
        pass
    elif not dbx_workflow_execution_table.exists():
        dbx_workflow_execution_table.create()
        log.debug("DBX tables added.")
    else:
        from ckan.model.meta import engine
        log.debug('IDS and DBX tables already exist')
        # Check if existing tables need to be updated
        inspector = Inspector.from_engine(engine)


class IdsDomainObject(DomainObject):
    '''Convenience methods for searching objects
    '''
    key_attr = 'id'

    @classmethod
    def get(cls, key, default=None, attr=None):
        '''Finds a single entity in the register.'''
        if attr is None:
            attr = cls.key_attr
        kwds = {attr: key}
        o = cls.filter(**kwds).first()
        if o:
            return o
        else:
            return default

    @classmethod
    def filter(cls, **kwds):
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kwds)


class IdsResource(IdsDomainObject):
    '''An IDS Resource
    '''
    def __repr__(self):
        return '<IdsResource id=%s>' % \
               (self.id)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

    def __init__(self, id=None):
        self.id = id

    def get_agreements(self, user_id=None):
        """ get the agreements for this resource """

        query = Session.query(IdsAgreement).filter(IdsAgreement.resource_id == self.id)

        if user_id is not None:
            query = query.filter(IdsAgreement.user_id == user_id)

        return query.all()


class IdsAgreement(IdsDomainObject):
    '''An agreement that has been made between a consumer and a provider data space connector
    '''
    def __repr__(self):
        return '<IdsAgreement id=%s resource_id=%s>' % \
               (self.id, self.resource_id)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

    def __init__(self, id=None, resource=None, user=None):
        self.id = id
        self.resource_id = resource.id
        self.user_id = user

    def get_workflows(self, user_id=None):
        """ get the agreements for this agreement """

        query = Session.query(WorkflowExecution).filter(WorkflowExecution.agreement_id == self.id)

        if user_id is not None:
            query = query.filter(IdsSubscription.user_id == user_id)

        return query.all()

    def get_subscriptions(self, user_id=None):
        """ get the agreements for this agreement """

        query = Session.query(IdsSubscription).filter(IdsSubscription.agreement_id == self.id)

        if user_id is not None:
            query = query.filter(IdsSubscription.user_id == user_id)

        return query.all()


class IdsSubscription(IdsDomainObject):
    '''A subscription that has been made between a consumer and a provider data space connector
    '''
    def __repr__(self):
        return '<IdsSubscription id=%s agreement_id=%s user_id=%s>' % \
               (self.id, self.agreement_id, self.user_id)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

    def __init__(self, id=None, agreement=None, user=None):
        self.id = id
        self.agreement_id = agreement.id
        self.user_id = user

class WorkflowExecution(IdsDomainObject):
    '''A workflow execution that has been initiated by a service consumer towards a service provider
    '''
    def __repr__(self):
        return '<WorkflowExecution id=%s agreement_id=%s user_id=%s workflow_name=%s>' % \
            (self.id, self.agreement_id, self.user_id, self.workflow_name)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')

    def __init__(self, id=None, agreement=None, user=None, workflow_name=None):
        self.id = id
        self.user_id = user
        self.workflow_name = workflow_name
        self.agreement_id = agreement.id



def define_ids_tables():

    global ids_agreement_table
    global ids_resource_table
    global ids_subscription_table
    global dbx_workflow_execution_table

    ids_resource_table = Table(
        'ids_resource',
        metadata,
        Column('id', types.UnicodeText, primary_key=True),
        Column('created', types.DateTime, default=datetime.datetime.utcnow)
    )

    ids_agreement_table = Table(
        'ids_agreement',
        metadata,
        Column('id', types.UnicodeText, primary_key=True),
        Column('resource_id', types.UnicodeText, ForeignKey('ids_resource.id')),
        Column('created', types.DateTime, default=datetime.datetime.utcnow)
    )

    ids_subscription_table = Table(
        'ids_subscription',
        metadata,
        Column('id', types.UnicodeText, primary_key=True),
        Column('agreement_id', types.UnicodeText, ForeignKey('ids_agreement.id')),
        Column('created', types.DateTime, default=datetime.datetime.utcnow)
    )

    dbx_workflow_execution_table = Table(
        'dbx_workflow_execution',
        metadata,
        Column('id', types.UnicodeText, primary_key=True),
        Column('agreement_id', types.UnicodeText, ForeignKey('ids_agreement.id')),
        Column('workflow_name', types.UnicodeText),
        Column('created', types.DateTime, default=datetime.datetime.utcnow)
    )

    mapper(
        IdsResource,
        ids_resource_table,
        properties={
            'agreements': relation(
                IdsAgreement,
                lazy=True,
                backref=u'resource',
            )}
    )

    mapper(
        IdsAgreement,
        ids_agreement_table,
        properties={
            'subscriptions': relation(
                IdsSubscription,
                lazy=True,
                backref=u'subscription',
            ),
            'workflow_executions': relation(
                WorkflowExecution,
                lazy=True,
                backref=u'workflow_execution',
            )}
    )

    mapper(IdsSubscription,
           ids_subscription_table,
           )

    mapper(WorkflowExecution,
           dbx_workflow_execution_table,
           )
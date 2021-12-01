from ckan.common import config
from ckanext.ids.dataspaceconnector.resourceapi import ResourceApi

class Connector:
    url = None
    auth = ()

    def __init__(self, url, username, password):
        self.url = url
        self.auth = ( username, password)

    def __init__(self):
        self.url = config.get('ckanext.ids.trusts_local_dataspace_connector_url')
        self.auth = (config.get('ckanext.ids.trusts_local_dataspace_connector_username'), config.get('ckanext.ids.trusts_local_dataspace_connector_password'))

    def get_resource_api(self):
        return ResourceApi(self.url, self.auth)
import json
import logging
from os.path import join as pathjoin

import requests
from requests.auth import HTTPBasicAuth
from ckan.common import config

from ckanext.ids.dataspaceconnector.resourceapi import ResourceApi

log = logging.getLogger("ckanext")


class ConnectorException(Exception):
    def __init__(self, m):
        self.message = m

    def __str__(self):
        return "CONNECTOR_EXCEPTION " + self.message


class Connector:
    url = None
    auth = ()

    def __init__(self, url, username, password):
        self.url = url
        self.auth = (username, password)
        self.broker_url = config.get('ckanext.ids.trusts_central_broker',
                                     'http://central-core:8282/infrastructure')

    def __init__(self):
        port = config.get('ckanext.ids.trusts_local_dataspace_connector_port',
                          '8080')
        self.url = config.get(
            'ckanext.ids.trusts_local_dataspace_connector_url') + ":" + str(
            port)
        self.auth = (
            config.get(
                'ckanext.ids.trusts_local_dataspace_connector_username'),
            config.get(
                'ckanext.ids.trusts_local_dataspace_connector_password'))
        self.broker_url = config.get('ckanext.ids.trusts_central_broker',
                                     'http://central-core:8282/infrastructure')

    def get_resource_api(self):
        return ResourceApi(self.url, self.auth)

    def search_broker(self, search_string: str,
                      limit: int = 100,
                      offset: int = 0):
        params = {"recipient": self.broker_url,
                  "limit": limit,
                  "offset": offset}
        headers = {"Content-type":"application/json",
                   "accept":"*/*"}

        url = pathjoin(self.url, "api/ids/search")
        data = search_string.encode("utf-8")
        response = requests.post(url=url,
                                 params=params,
                                 data=data,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))
        if response.status_code > 299 or response.text is None:
            log.error("Got code " + str(response.status_code) + " in search")
            log.error("Response Text: " + str(response.text))
            log.error("Provided Data: " + data.decode("utf-8"))
            log.error("URL: " + url)
            log.error("PARAMS: "+json.dumps(params,indent=2))

            raise ConnectorException("Code: "+ str(response.status_code)+
                                     " Text: "+ str(response.text))

        return response.text

    def query_broker(self, query_string: str):
        params = {"recipient": self.broker_url}
        url = pathjoin(self.url, "api/ids/query")
        data = query_string.encode("utf-8")
        response = requests.post(url=url,
                                 params=params,
                                 data=data,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))
        if response.status_code > 299 or response.text is None:
            log.error("Got code " + str(response.status_code) + " in search")
            log.error("Provided Data: " + data.decode("utf-8"))
            raise ConnectorException("Code: "+ str(response.status_code)+
                                     " Text: "+ str(response.text))

        return response.text

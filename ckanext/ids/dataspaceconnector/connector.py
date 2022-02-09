import json
import logging
from os.path import join as pathjoin

import requests
from ckan.common import config
from requests.auth import HTTPBasicAuth

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

    # def __init__(self, url, username, password):
    #     self.url = url
    #     self.auth = (username, password)
    #     self.broker_url = config.get('ckanext.ids.trusts_central_broker',
    #                                  'http://central-core:8282/infrastructure')
    #     self.broker_url = 'http://central-core:8080/infrastructure'

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
        self.broker_url = 'http://central-core:8080/infrastructure'
        self.broker_knows_us = False

    def get_resource_api(self):
        return ResourceApi(self.url, self.auth)

    def search_broker(self, search_string: str,
                      limit: int = 100,
                      offset: int = 0):
        if not self.broker_knows_us:
            self.announce_to_broker()
        params = {"recipient": self.broker_url,
                  "limit": limit,
                  "offset": offset}
        headers = {"Content-type": "application/json",
                   "accept": "*/*"}

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
            log.error("PARAMS: " + json.dumps(params, indent=2))

            raise ConnectorException("Code: " + str(response.status_code) +
                                     " Text: " + str(response.text))

        return response.text

    def query_broker(self, query_string: str, return_if_417=False):
        if not self.broker_knows_us and not return_if_417:
            self.announce_to_broker()
        params = {"recipient": self.broker_url}
        url = pathjoin(self.url, "api/ids/query")
        data = query_string.encode("utf-8")
        response = requests.post(url=url,
                                 params=params,
                                 data=data,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))
        if return_if_417:
            return response
        if response.status_code > 299 or response.text is None:
            log.error("Got code " + str(response.status_code) + " in search")
            log.error("Provided Data: " + data.decode("utf-8"))
            raise ConnectorException("Code: " + str(response.status_code) +
                                     " Text: " + str(response.text))

        return response.text

    def ask_broker_description(self, element_uri: str):
        resource_contract_tuples = []
        if not self.broker_knows_us:
            self.announce_to_broker()
        if len(element_uri) < 5 or ":" not in element_uri:
            return {}
        params = {"recipient": self.broker_url,
                  "elementId": element_uri}
        url = pathjoin(self.url, "api/ids/description")
        response = requests.post(url=url,
                                 params=params,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))
        if response.status_code > 299 or response.text is None:
            log.error("Got code " + str(response.status_code) + " in describe")
            raise ConnectorException("Code: " + str(response.status_code) +
                                     " Text: " + str(response.text))

        graphs = response.json()
        return graphs

    def announce_to_broker(self):
        # If for some reason this is the first resource we send to the
        # broker, we have to first register this connector.
        # We check the broker response, because if we register when
        # there is already an index for this connector, all resources
        # are deleted :S
        q = """SELECT ?resultUri  { GRAPH ?g  { 
            ?resultUri a <https://w3id.org/idsa/core/Resource> } } """
        r = self.query_broker(q, return_if_417=True)
        self.broker_knows_us = True
        if r.status_code == 417 \
                and "empty" in str(r.json()).lower():
            params = {"recipient": self.broker_url}
            url = pathjoin(self.url, "api/ids/connector/update")
            response = requests.post(url=url,
                                     params=params,
                                     auth=HTTPBasicAuth(self.auth[0],
                                                        self.auth[1]))
            self.broker_knows_us = response.status_code < 299
        return self.broker_knows_us

    def send_resource_to_broker(self, resource_uri: str):
        if not self.broker_knows_us:
            self.announce_to_broker()
        params = {"recipient": self.broker_url,
                  "resourceId": resource_uri}
        url = pathjoin(self.url, "api/ids/resource/update")
        response = requests.post(url=url,
                                 params=params,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))

        return response.status_code < 299

import datetime
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
            'ckanext.ids.trusts_local_dataspace_connector_url',
            'provider-core') + ":" + str(
            port)
        self.auth = (
            config.get(
                'ckanext.ids.trusts_local_dataspace_connector_username'),
            config.get(
                'ckanext.ids.trusts_local_dataspace_connector_password'))
        # ToDo Make sure this config is working
        self.broker_url = config.get('ckanext.ids.trusts_central_broker',
                                     'http://central-core:8282/infrastructure')
        # self.broker_url = 'http://central-core:8080/infrastructure'
        self.broker_knows_us_timestamp = None
        self.broker_knows_us_limit = 10
        self.my_catalog_ids = []
        self.resourceAPI = ResourceApi(self.url, self.auth)

    def broker_knows_us(self):
        if self.broker_knows_us_timestamp is None:
            return False
        tnow = datetime.datetime.now()
        dt = tnow - self.broker_knows_us_timestamp
        if dt.total_seconds() > self.broker_knows_us_limit:
            return False
        log.debug("\n________ BROKER STILLS KNOWS US _______________")
        return True

    def get_resource_api(self):
        return self.resourceAPI

    def search_broker(self, search_string: str,
                      limit: int = 100,
                      offset: int = 0):
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
        if not return_if_417:
            self.announce_to_broker()
        params = {"recipient": self.broker_url}
        url = pathjoin(self.url, "api/ids/query")
        data = query_string.encode("utf-8")
        #log.error("Querying "+url+"\nwith "
        #                          "string"+query_string+" ->
        #                          "+self.broker_url)
        #log.error("\n|\n|\n|\n|\n|------------")
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

    def ask_broker_for_description(self, element_uri: str):
        self.announce_to_broker()
        resource_contract_tuples = []

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

    def fetch_catalog_ids(self):
        rj = self.resourceAPI.get_catalogs()
        self.my_catalog_ids = [x["_links"]["self"]["href"]
                               for x in rj["_embedded"]["catalogs"]]
        return self.my_catalog_ids

    def _build_query_my_resources(self):
        q = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT ?resultUri ?conn { GRAPH ?g  { 
            """
        qparts = []
        for cat in self.my_catalog_ids:
            qpart = """
              {
              ?resultUri a <https://w3id.org/idsa/core/Resource> .
              ?conn <https://w3id.org/idsa/core/offeredResource> ?resultUri .
              ?conn owl:sameAs <""" + cat + ">. "
            qpart += "}"
            qparts.append(qpart)

        q += "\nUNION\n".join(qparts)
        q += "} }"
        return q

    def announce_to_broker(self):
        # If for some reason this is the first resource we send to the
        # broker, we have to first register this connector.
        # We check the broker response, because if we register when
        # there is already an index for this connector, all resources
        # are deleted :S
        if self.broker_knows_us():
            return True

        self.fetch_catalog_ids()
        q = self._build_query_my_resources()
        r = self.query_broker(q, return_if_417=True)

        self.broker_knows_us_timestamp = datetime.datetime.now()

        need_to_announce = False
        # If the Index is empty, the broker is probably fresh restarted
        if r.status_code == 417 \
                and "empty" in str(r.json()).lower():
            need_to_announce = True

        # If there are no records for this connector, it doesn't harm to
        # announce ourselves again
        numlines = -1
        if r.status_code < 299:
            numlines = len([x for x in r.text.split("\n")])
            if numlines < 1:  # It should contain at least the header line
                need_to_announce = True

        if need_to_announce:
            params = {"recipient": self.broker_url}
            url = pathjoin(self.url, "api/ids/connector/update")
            response = requests.post(url=url,
                                     params=params,
                                     auth=HTTPBasicAuth(self.auth[0],
                                                        self.auth[1]))
            if response.status_code < 299:
                self.broker_knows_us_timestamp = datetime.datetime.now()
        else:
            log.debug("\n________ NO NEED TO ANNOUNCE US _______________")
            log.debug(str(r.status_code) + "  with lines: " + str(numlines))
            log.debug("\n_______________________________________________\n")
            self.broker_knows_us_timestamp = datetime.datetime.now()

        return True

    def send_resource_to_broker(self, resource_uri: str):
        self.announce_to_broker()
        params = {"recipient": self.broker_url,
                  "resourceId": resource_uri}
        url = pathjoin(self.url, "api/ids/resource/update")
        response = requests.post(url=url,
                                 params=params,
                                 auth=HTTPBasicAuth(self.auth[0],
                                                    self.auth[1]))
        log.debug("------ \n\n REQUEST TO ADD TO BROKER " + url + " :")
        log.debug(json.dumps(params, indent=1))
        log.debug("------ RESPONSE OF SEND RESOURCE TO BROKER IS :  ")
        log.debug(response.text)
        log.debug("\n\n\n\n\n\n\n ---------------------------------------\n")
        return response.status_code < 299

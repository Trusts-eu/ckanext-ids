import logging

import ckan.plugins.toolkit as toolkit

import pathlib
from ckanext.ids.model import IdsResource, IdsAgreement, IdsSubscription
from urllib.parse import urlparse
from ckanext.ids.dataspaceconnector.resourceapi import ResourceApi
from ckanext.ids.dataspaceconnector.subscriptionapi import SubscriptionApi
from ckanext.ids.dataspaceconnector.idsapi import IdsApi

log = logging.getLogger("ckanext.ids.dsc.subscribe")

consumerUrl = None
local_node = None
consumer = None
username = None
password = None
consumer_alias = None


class Subscription:
    offer_url = None
    provider_alias = None
    agreement_url = None
    first_artifact = None
    remote_artifact = None
    data_source = None
    endpoint = None
    route = None


    def __init__(self, offer_url, agreement, user_email):
        self.offer_url = offer_url
        self.agreement = agreement
        self.user_email = user_email
        consumerUrl = toolkit.config.get('ckanext.ids.trusts_local_dataspace_connector_url') + ":" + toolkit.config.get('ckanext.ids.trusts_local_dataspace_connector_port')
        username = toolkit.config.get('ckanext.ids.trusts_local_dataspace_connector_username')
        password = toolkit.config.get('ckanext.ids.trusts_local_dataspace_connector_password')
        consumer_alias = consumerUrl

        consumer = IdsApi(consumerUrl, auth=(username, password))
        local_node = toolkit.config.get("ckanext.ids.trusts_local_dataspace_connector_url")

        parsed_url = urlparse(offer_url)
        self.provider_alias = parsed_url.scheme + "://" + parsed_url.netloc


# Consumer

    def subscribe(self):
       # self.create_data_source()
       # log.debug("creating endpoint...")
       # self.create_endpoint()
       # log.debug("endpoint created!")
       #  self.link_endpoint_data_source()
       # log.debug("creating route...")
       # self.create_route()
       # log.debug("route created!")
       # log.debug("linking endpoint to route...")
       # self.link_endpoint_route()
       # log.debug("linking completed!")
        log.debug("getting local agreement")
        local_agreement = self.agreement
        log.debug("agreement retrieved!")
        log.debug("getting request")
        consumerResources = ResourceApi(consumerUrl)
        artifacts = consumerResources.get_artifacts_for_agreement(local_agreement.id)
        first_artifact = artifacts["_embedded"]["artifacts"][0]["_links"]["self"]["href"]
        representations = consumerResources.get_representations_for_artifact(first_artifact)
        first_representation = representations["_embedded"]["representations"][0]["_links"]["self"]["href"]
        requests = consumerResources.get_requests_for_representation(first_representation)
        first_request = requests["_embedded"]["resources"][0]["_links"]["self"]["href"]
        log.debug("Request retrieved!")
        # subscribe to the requested artifact
        log.debug("Creating subscription client...")
        consumerSub = SubscriptionApi(consumerUrl)
        log.debug("Client created!")
        data = {
            "title": "CKAN on " + local_node + " asset subscription: " + self.offer_url,
            "description": first_request,
            "target": first_request,
            "location": "http://note-service:5055/notify?ids-toemail=" + self.user_email,
            "subscriber":  "http://note-service:5055/notify?ids-toemail=" + self.user_email,
            "pushData": "false",
        }
        log.debug(data)
        log.debug("creating non-IDS subscription...")
        response = consumerSub.create_subscription(data=data)
        log.debug("non-IDS subscription created!")
        log.debug("Persisting subscription...")
        local_subscription = IdsSubscription(id=response, agreement=local_agreement, user=username)
        local_subscription.save()
        log.debug("Subscription persisted!")
        log.debug(response)

        ## this is used to create ids subscription
        ## subscribe to the remote offer
        log.debug("Creating IDS subscription...")
        data = {
            "title": "DSC on " + local_node + "asset subscription: " + self.offer_url,
            "description": self.offer_url,
            "target": self.offer_url,
            "location": consumerUrl + "/api/ids/data",
            "subscriber": consumerUrl,
            "pushData": "true",
        }
        log.debug(data)
        response = consumerSub.subscription_message(
            data=data, params={"recipient": self.provider_alias + "/api/ids/data"}
        )
        log.debug(response.status_code)
        log.debug(response.text)
        if response.status_code == 200:
            print(response.text)
            return True
        else:
            return False


    def create_data_source(self):
        data = {
            "authentication": {
                "key": "dsc_user_read",
                "value": toolkit.config.get('ckanext.ids.trusts_local_dataspace_connector_password')
            },
            "type": "REST"
        }
        data_source = consumer.create_data_source(data)
        self.data_source = data_source["id"]
        return data_source

    def create_endpoint(self):
        data = {
            "location": "http://note-service:5055/notify?ids-toemail=" + self.user_email,
            "type": "GENERIC"
        }
        endpoint = consumer.create_endpoint(data)
        self.endpoint = pathlib.PurePath(endpoint["_links"]["self"]["href"]).name
        return endpoint

    def link_endpoint_data_source(self):
        response = consumer.link_endpoint_datasource(self.endpoint, self.data_source)
        return response

    def create_route(self):
        data = {
            "title": "Notification service Update Route",
            "deploy": "Camel"
        }
        response = consumer.create_route(data)
        self.route = response["_links"]["self"]["href"]
        return response

    def link_endpoint_route(self):
        response = consumer.link_route_endpoint(pathlib.PurePath(self.route).name, self.endpoint)
        return response
#
# Copyright 2020 Fraunhofer Institute for Software and Systems Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# forked from https://github.com/International-Data-Spaces-Association/DataspaceConnector/blob/main/scripts/tests/resourceapi.py
# modified by karampatakiss

import requests
import json
import cachetools.func

# Suppress ssl verification warning
requests.packages.urllib3.disable_warnings()


class ResourceApi:
    session = None
    recipient = None

    def __init__(self, recipient, auth=("admin", "password")):
        self.session = requests.Session()
        self.session.auth = auth
        self.session.verify = False

        self.recipient = recipient

    def create_catalog(self, data={}):
        response = self.session.post(self.recipient + "/api/catalogs", json=data)
        return response.headers["Location"]

    def resource_exists(self, offer_uri:str):
        if not offer_uri.startswith(self.recipient + "/api/"):
            raise ValueError
        response = self.session.get(offer_uri)
        return response.status_code < 399

    @cachetools.func.ttl_cache(3)
    def get_catalogs(self, data={}):
        response = self.session.get(self.recipient + "/api/catalogs")
        print("GETting catalogues returned:", response.status_code,
              "url:", self.recipient+"/api/catalogs")
        return json.loads(response.text)

    def create_offered_resource(self, data={}):
        response = self.session.post(self.recipient + "/api/offers", json=data)
        return response.headers["Location"]

    def update_offered_resource(self, offered_resource, data={}):
        response = self.session.put(offered_resource, json=data)
        return response.status_code == 204

    def delete_offered_resource(self, offered_resource, data={}):
        response = self.session.delete(offered_resource, json=data)
        return response.status_code == 204

    def create_representation(self, data={}):
        response = self.session.post(self.recipient + "/api/representations", json=data)
        return response.headers["Location"]

    def update_representation(self, representation_iri, data={}):
        response = self.session.put(representation_iri, json=data)
        return response.status_code == 204

    def delete_representation(self, data={}):
        response = self.session.delete(data.representation_iri, json=data)
        return response.status_code == 204

    def get_artifact(self, url):
        response = self.session.get(url)
        print("GETting artifact:", response.status_code,
              "url:", url)
        return json.loads(response.text)

    def create_artifact(self, data={"value": "SOME LONG VALUE"}):
        response = self.session.post(self.recipient + "/api/artifacts", json=data)
        location = response.headers["Location"]
        return location

    def update_artifact(self, artifact, data) -> bool:
        response = self.session.put(artifact, json=data)
        return response.status_code == 204

    def delete_artifact(self, artifact, data) -> bool:
        response = self.session.delete(artifact, json=data)
        return response.status_code == 204

    def get_new_policy(self, data):
        response = self.session.post(self.recipient + "/api/examples/policy", json=data)
        return response.content


    def create_contract(
            self,
            data={
                "start": "2021-04-06T13:33:44.995+02:00",
                "end": "2021-12-06T13:33:44.995+02:00",
            },
    ):
        response = self.session.post(self.recipient + "/api/contracts", json=data)
        return response.headers["Location"]

    def create_rule(
            self,
            data={
                "value": """{
            "@context" : {
                "ids" : "https://w3id.org/idsa/core/",
                "idsc" : "https://w3id.org/idsa/code/"
            },
            "@type": "ids:Permission",
            "@id": "https://w3id.org/idsa/autogen/permission/cf1cb758-b96d-4486-b0a7-f3ac0e289588",
            "ids:action": [
                {
                "@id": "idsc:USE"
                }
            ],
            "ids:description": [
                {
                "@value": "provide-access",
                "@type": "http://www.w3.org/2001/XMLSchema#string"
                }
            ],
            "ids:title": [
                {
                "@value": "Example Usage Policy",
                "@type": "http://www.w3.org/2001/XMLSchema#string"
                }
            ]
            }"""
            },
    ):
        response = self.session.post(self.recipient + "/api/rules", json=data)
        return response.headers["Location"]

    def get_contracts(self, url):
        contracts_url = url + "/contracts"
        response = self.session.get(contracts_url)
        print("GETting contracts:", response.status_code,
              "url:", contracts_url)
        if response.status_code > 299:
            raise IOError(response.text)
        return json.loads(response.text)

    def add_resource_to_catalog(self, catalog, resource):
        return self.session.post(
            catalog + "/offers", json=self.toListIfNeeded(resource)
        )

    def add_catalog_to_resource(self, resource, catalog):
        return self.session.post(
            resource + "/catalogs", json=self.toListIfNeeded(catalog)
        )

    def add_representation_to_resource(self, resource, representation):
        return self.session.post(
            resource + "/representations", json=self.toListIfNeeded(representation)
        )

    def add_artifact_to_representation(self, representation, artifact):
        return self.session.post(
            representation + "/artifacts", json=self.toListIfNeeded(artifact)
        )

    def add_contract_to_resource(self, resource, contract):
        return self.session.post(
            resource + "/contracts", json=self.toListIfNeeded(contract)
        )

    def add_rule_to_contract(self, contract, rule):
        return self.session.post(contract + "/rules", json=self.toListIfNeeded(rule))

    def toListIfNeeded(self, obj):
        if isinstance(obj, list):
            return obj
        else:
            return [obj]

    def get_data(self, artifact):
        return self.session.get(artifact + "/data")

    def get_artifacts_for_agreement(self, agreement):
        return json.loads(self.session.get(agreement + "/artifacts").text)

    def get_representations_for_artifact(self, artifact):
        return json.loads(self.session.get(artifact + "/representations").text)

    def get_requests_for_representation(self, representation):
        return json.loads(self.session.get(representation + "/requests").text)

    def descriptionRequest(self, recipient, elementId):
        url = self.recipient + "/api/ids/description"
        params = {}
        if recipient is not None:
            params["recipient"] = recipient
        if elementId is not None:
            params["elementId"] = elementId

        response = self.session.post(url, params=params)
        return json.loads(response.text)

    def contractRequest(self, recipient, resourceId, artifactId, download, contract):
        url = self.recipient + "/api/ids/contract"
        params = {}
        if recipient is not None:
            params["recipient"] = recipient
        if resourceId is not None:
            params["resourceIds"] = resourceId
        if artifactId is not None:
            params["artifactIds"] = artifactId
        if download is not None:
            params["download"] = download

        response = self.session.post(
            url, params=params, json=self.toListIfNeeded(contract)
        )
        response_content = json.loads(response.text)
        if response.status_code > 299:
            raise IOError(response_content)
        return response_content

    def toListIfNeeded(self, obj):
        if isinstance(obj, list):
            return obj
        else:
            return [obj]



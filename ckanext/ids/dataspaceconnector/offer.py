"""
The Offer Model of the Dataspace Connector
{
    "title": "string",
    "description": "string",
    "keywords": [
        "string"
    ],
    "publisher": "string",
    "language": "string",
    "license": "string",
    "sovereign": "string",
    "endpointDocumentation": "string",
    "samples": [
        "string"
    ],
    "paymentMethod": "undefined"
}
"""


class Offer(dict):
    title: None
    description: None
    keywords: []
    publisher: None
    language: None
    license: None
    sovereign: None
    endpointDocumentation: None
    samples: []
    paymentMethod: None
    catalog_iri: ""
    offer_iri: ""

    def __init__(self, pkg_dict):
        self.title = pkg_dict['title']
        self.keywords = pkg_dict['tags']
        self.publisher = pkg_dict['owner_org']
        self.license = pkg_dict['license_url']
        if "extras" in pkg_dict:
            for entry in pkg_dict["extras"]:
                if entry["key"] == "catalog":
                    self.catalog_iri = entry["value"]
                if entry["key"] == "offers":
                    self.offer_iri = entry["value"]
        else:
            self.catalog_iri = None
            self.offer_iri = None

"""
{
  "author": null, 
  "author_email": null, 
  "creator_user_id": "60cf572d-5de0-4ef5-b661-51bfd332f3c2", 
  "extras": [
    {
      "key": "artifact", 
      "value": "http://localhost:8089/api/artifacts/4797ba8e-b6e6-470a-93a0-84f97432ff20"
    }, 
    {
      "key": "catalog", 
      "value": "http://localhost:8089/api/catalogs/f6920af2-9697-48b6-aa8d-08f62956bf89"
    }, 
    {
      "key": "offers", 
      "value": "http://localhost:8089/api/offers/2fdc1dc4-d7fa-4164-841b-8ccea0d8a6f7"
    }, 
    {
      "key": "representation", 
      "value": "http://localhost:8089/api/representations/ddf5187b-0710-4eb7-a013-b4044e435ac2"
    }
  ], 
  "groups": [], 
  "id": "24b10e55-e01d-48a1-894a-c576ff532b15", 
  "isopen": true, 
  "license_id": "cc-by", 
  "license_title": "Creative Commons Attribution", 
  "license_url": "http://www.opendefinition.org/licenses/cc-by", 
  "maintainer": null, 
  "maintainer_email": null, 
  "metadata_created": "2021-11-25T16:43:17.205565", 
  "metadata_modified": "2021-11-30T13:42:23.994829", 
  "name": "test2", 
  "notes": null, 
  "num_resources": 3, 
  "num_tags": 0, 
  "organization": {
    "approval_status": "approved", 
    "created": "2021-11-24T17:19:04.644099", 
    "description": "", 
    "id": "e5064645-2841-4a37-bb48-279f68c5bc2b", 
    "image_url": "", 
    "is_organization": true, 
    "name": "test", 
    "state": "active", 
    "title": "test", 
    "type": "organization"
  }, 
  "owner_org": "e5064645-2841-4a37-bb48-279f68c5bc2b", 
  "private": false, 
  "relationships_as_object": [], 
  "relationships_as_subject": [], 
  "resources": [
    {
      "cache_last_updated": null, 
      "cache_url": null, 
      "configurationdatetime_date": "", 
      "configurationdatetime_time": "", 
      "created": "2021-11-25T16:43:47.682071", 
      "deploymentdatetime_date": "", 
      "deploymentdatetime_time": "", 
      "description": null, 
      "format": "", 
      "hash": "", 
      "id": "6caffd25-c361-4b6f-b1c6-89f03bf313b1", 
      "last_modified": null, 
      "metadata_modified": "2021-11-25T16:43:47.669803", 
      "mimetype": null, 
      "mimetype_inner": null, 
      "name": "", 
      "package_id": "24b10e55-e01d-48a1-894a-c576ff532b15", 
      "position": 0, 
      "readmedatetime_date": "", 
      "readmedatetime_time": "", 
      "resource_type": "deploymentPhoto", 
      "size": null, 
      "state": "active", 
      "url": "", 
      "url_type": null
    }
  ], 
  "state": "active", 
  "tags": [], 
  "theme": "https://trusts.org/vacabulary/themes/Health", 
  "title": "test", 
  "type": "dataset", 
  "url": null, 
  "version": null
}
"""
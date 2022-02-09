import rdflib

def URI(somestr: str):
    if isinstance(somestr, rdflib.URIRef):
        return somestr
    if somestr.startswith("<"):
        somestr = somestr[1:]
    if somestr.endswith(">"):
        somestr = somestr[:-1]
    return rdflib.URIRef(somestr)


empty_result = {
    "author": None,
    "author_email": None,
    "creator_user_id": "__MISSING__", #  (/)
    "id": "__MISSING__",   # (/)
    "isopen": None,    # (/)
    "license_id": "__MISSING__",  # (/)
    "license_title": "__MISSING__",  # (/)
    "license_url": "__MISSING__",   # (/)
    "maintainer": None, # (/)
    "maintainer_email": None,  # (/)
    "metadata_created": "__MISSING__",   # (/)
    "metadata_modified": "__MISSING__",   # (/)
    "name": "__MISSING__", # (/)
    "notes": None,  # (/)
    "num_resources": 0,  # (/)
    "num_tags": 0, # (/)
    "owner_org": "__MISSING__",   # (/)
    "private": None, # (/)
    "state": "active", # (/)
    "theme": "__MISSING__",   # (/)
    "title": "__MISSING__",   # (/)
    "type": "__MISSING__",   # (/)
    "url": None,  # (/)
    "version": "__MISSING__",  # (/)
    "tags": [],  # (/)
    "groups": [],  # (/)
    "dataset_count": 0,   # (/)
    "service_count": 0,  # (/)
    "application_count": 0,  # (/)
    "relationships_as_object": [], # (/)
    "relationships_as_subject": [], # (/)
    "resources": [ ],
    "organization": {}  # (/)
}

empty_organization = {
  "id": "52bc9332-2ba1-4c4f-bf85-5a141cd68423",
  "name": "orga1",
  "title": "Orga1",
  "type": "organization",
  "description": "",
  "image_url": "",
  "created": "2022-02-02T16:32:58.653424",
  "is_organization": True,
  "approval_status": "approved",
  "state": "active"
}

empty_resource = {
            "artifact":  "__MISSING__",
            "cache_last_updated": None,
            "cache_url": None,
            "created":  "__MISSING__",
            "description": "<https://w3id.org/idsa/core/description>",
            "format":  "__MISSING__",
            "hash": "",
            "id":  "__MISSING__",
            "last_modified":  "<https://w3id.org/idsa/core/modified>",
            "metadata_modified":  "<https://w3id.org/idsa/core/modified>",
            "mimetype":  "__MISSING__",
            "mimetype_inner": None,
            "name":  "__MISSING__",
            "package_id":  "__MISSING__",
            "position": 0,
            "representation":  "<https://w3id.org/idsa/core/representation>",
            "resource_type": "resource",
            "size":  "__MISSING__",
            "state": "active",
            "url": "__MISSING__",
            "url_type": "upload"
        }

translation_ckanFromBroker_result = {
    "maintainer" : URI("<https://w3id.org/idsa/core/publisher>"),
    "title": URI("<https://w3id.org/idsa/core/title>"),
    "version": URI("<https://w3id.org/idsa/core/version>"),
    "owner_org": URI("<https://w3id.org/idsa/core/sovereign>"),
    "name":URI("<https://w3id.org/idsa/core/title>"),
    "metadata_modified":URI("<https://w3id.org/idsa/core/modified>"),
    "metadata_created": URI("<https://w3id.org/idsa/core/created>"),
    "creator_user_id": URI("<https://w3id.org/idsa/core/sovereign>")
}
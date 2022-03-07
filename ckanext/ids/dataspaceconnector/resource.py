class Resource(dict):
    representation_iri: None
    artifact_iri: None

    def __init__(self, resource_dict):
        if "representation" in resource_dict:
            self.representation_iri = resource_dict["representation"]
        else:
            self.representation_iri = None
        if "artifact" in resource_dict:
            self.artifact_iri = resource_dict["artifact"]
        else:
            self.artifact_iri = None
        if 'service_accessURL' in resource_dict:
            self.service_accessURL = resource_dict["service_accessURL"]
        else:
            self.service_accessURL = None

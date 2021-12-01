class Resource(dict):
    representation_iri: None
    artifact_iri: None

    def __init__(self, resource_dict):
        if "representation" in resource_dict:
            self.representation_iri = resource_dict["representation"]
        if "artifact" in resource_dict:
            self.artifact_iri = resource_dict["artifact"]
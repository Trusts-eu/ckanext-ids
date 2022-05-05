class Resource(dict):
    representation_iri: None
    artifact_iri: None
    service_accessURL: None
    title: None
    description: None
    mediaType: None
    filename: None

    def __init__(self, resource_dict):
        self.service_accessURL = None
        self.representation_iri = None
        self.artifact_iri = None
        self.title = ""
        self.description = ""
        self.mediaType = ""

        if "representation" in resource_dict:
            self.representation_iri = resource_dict["representation"]
        if "artifact" in resource_dict:
            self.artifact_iri = resource_dict["artifact"]
        if 'service_accessURL' in resource_dict:
            self.service_accessURL = resource_dict["service_accessURL"]
        if 'description' in resource_dict:
            self.description = resource_dict['description']
        if 'mimetype' in resource_dict:
            self.mediaType = resource_dict['mimetype']

        # The artifact's title can be taken from one of several
        if 'name' in resource_dict:
            self.title = resource_dict["name"]
        if 'title' in resource_dict:
            self.title = resource_dict["title"]
        if 'resource_type' in resource_dict and resource_dict["resource_type"]:
            self.title = resource_dict["resource_type"] +"__"+ self.title




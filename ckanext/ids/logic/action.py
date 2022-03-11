from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.dataspaceconnector.offer import Offer
from ckanext.ids.dataspaceconnector.resource import Resource


def delete_from_dataspace_connector(data):
    local_resource_dataspace_connector = Connector().get_resource_api()
    offer = Offer(data)
    for value in data["resources"]:
        # this has also to run for every resource
        resource = Resource(value)
        if resource.representation_iri is not None:
            local_resource_dataspace_connector.delete_representation(resource)
        if resource.artifact_iri is not None:
            local_resource_dataspace_connector.delete_artifact(
                resource.artifact_iri, data={})
    if offer.offer_iri is not None:
        local_resource_dataspace_connector.delete_offered_resource(offer)

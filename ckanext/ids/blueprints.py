import json

from flask import Blueprint, jsonify, make_response, request
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from ckan.common import _, config
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.plugins as plugins
import ckan.model as model
from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.dataspaceconnector.offer import Offer
from ckanext.ids.dataspaceconnector.resource import Resource
from ckanext.ids.dataspaceconnector.contract import Contract
import requests
import logging

from werkzeug.datastructures import ImmutableMultiDict

tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
ValidationError = logic.ValidationError

ids = Blueprint(
    'ids',
    __name__
)

ids_actions = Blueprint(
    'ids_actions',
    __name__
)

log = logging.getLogger(__name__)


def request_contains_mandatory_files():
    return request.files['Deployment file (docker-compose.xml) - mandatory-upload'].filename != ''


@ids.route('/dataset/<id>/resources/create', methods=['POST'])
def create(id):
    # get clean data from the form, data will hold the common meta for all resources
    data = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
    data['package_id'] = id
    to_delete = ['clear_upload', 'save']

    # add fields ending with url in to_delete dictionary
    for field in data:
        if field.endswith('url') and len(field) > 3:
            to_delete.append(field)

    # these are not needed on the schema so we remove them

    for deletable in to_delete:
        del data[deletable]

    resources = []
    for file in request.files:
        # create a new resource dictionary from a copy of the common
        resource = data.copy()
        files = ImmutableMultiDict([(file, request.files[file])])
        # add the file
        resource.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(files)))))
        # file input field from the form will have a different name, we need to change this in upload
        resource['upload'] = resource[file]
        resource['name'] = resource[file].filename
        resource['url'] = resource[file].filename
        # get the name of the file to add it as resource_type
        resource['resource_type'] = resource[file].name.split("-upload",1)[0]
        del resource[file]
        # add the final resource on the table
        resources.append(resource)

    # iterate through all resources and add them on the package
    for resource in resources:
        toolkit.get_action('resource_create')(None, resource)

    revise_package_dict = {
        "match": {
            "name": id
        },
        "update": {
            "state": "active"
        }
    }
    try:
        toolkit.get_action("package_revise")(None, revise_package_dict )
    # unlikely to happen, but just to demonstrate error handling
    except (ValidationError):
        return base.abort(404, _(u'Dataset not found'))
    # redirect tp dataset read page
    return toolkit.redirect_to('dataset.read',
                        id=id)


@ids.route('/dataset/<id>/resources/delete', methods=['DELETE'])
def delete(id):
    return "deleted"


def push_package_task(dataset_dict):
    return push_to_dataspace_connector(dataset_dict)


def push_organization_task(organization_dict):
    action= 'organization_create'
    push_to_central(data=organization_dict, action=action)


def push_to_central(data, action):
    # We'll use the package_create function to create a new dataset.
    node_url = config.get('ckanext.ids.trusts_central_node_ckan')
    url = node_url + action
    # we need to check if the organization exists
    response = requests.post(url, json=data)
    #handle error
    assert response.status_code == 200


def push_to_dataspace_connector(data):
    c = plugins.toolkit.g
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               }
    local_resource_dataspace_connector = Connector().get_resource_api()
    # sync calls to the dataspace connector to create the appropriate objects
    # this will be constant.
    # It might cause an error if the connector does not persist it's data. A restart should fix the problem
    catalog = config.get("ckanext.ids.connector_catalog_iri")
    # try to populate this with fields from the package
    offer = Offer(data)
    if offer.offer_iri is None:
        offers = local_resource_dataspace_connector.create_offered_resource(Offer(data))
        local_resource_dataspace_connector.add_resource_to_catalog(catalog, offers)
    else:
        local_resource_dataspace_connector.update_offered_resource(offer)
        offers = offer.offer_iri
    # FIXME put these in an object and create a nice method
    extras = [{"key": "catalog", "value": catalog}, {"key": "offers", "value": offers}]
    for value in data["resources"]:
        # this has also to run for every resource
        resource = Resource(value)
        if resource.representation_iri is None:
            representation = local_resource_dataspace_connector.create_representation()
            local_resource_dataspace_connector.add_representation_to_resource(offers, representation)
        else:
            local_resource_dataspace_connector.update_representation(resource)
            representation = resource.representation_iri

        if resource.artifact_iri is None:
            artifact = local_resource_dataspace_connector.create_artifact(data={"accessUrl": value["url"]})
            local_resource_dataspace_connector.add_artifact_to_representation(representation, artifact)
        else:
            local_resource_dataspace_connector.update_artifact(resource.artifact_iri, data={"accessUrl": value["url"]})
            artifact = resource.artifact_iri

        # add these on the resource meta
        patch_data = {"id": value["id"], "representation": representation, "artifact": artifact}
        logic.action.patch.resource_patch(context, data_dict=patch_data)

    updated_package = toolkit.get_action("package_patch")(context, {"id": data["id"], "extras": extras})
    return updated_package

def delete_from_dataspace_connector(data):
    c = plugins.toolkit.g
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               }
    local_resource_dataspace_connector = Connector().get_resource_api()
    catalog = config.get("ckanext.ids.connector_catalog_iri")
    offer = Offer(data)
    for value in data["resources"]:
        # this has also to run for every resource
        resource = Resource(value)
        if resource.representation_iri is not None:
            local_resource_dataspace_connector.delete_representation(resource)
        if resource.artifact_iri is not None:
            local_resource_dataspace_connector.delete_artifact(resource.artifact_iri, data={})
    if offer.offer_iri is not None:
            local_resource_dataspace_connector.delete_offered_resource(offer)
    return


def transform_url(url):
    site_url = toolkit.config.get('ckan.site_url')
    log.info("Transforming url: %s", url)
    log.debug("ckan.site_url is set to: %s", site_url)
    log.debug(url)
    # splitting the url based on the ckan.site_url setting
    resource_url_part = url.split(site_url,1) [1]
    transformed_url = toolkit.config.get('ckanext.ids.central_node_connector_url') + toolkit.config.get('ckanext.ids.local_node_name') + "/ckan/5000" + resource_url_part
    log.info("URL is now: %s", transformed_url)
    return transformed_url


@ids_actions.route('/ids/actions/push_package/<id>', methods=['GET'])
def push_package(id):
    package_meta = toolkit.get_action("package_show")(None, {"id": id})
    # for index, resource in enumerate(package_meta['resources']):
    #    package_meta['resources'][index]['url_type'] = ''
    #    package_meta['resources'][index]['url'] = transform_url(resource['url'])
    # this is the asynchronous task
    # response = toolkit.enqueue_job(push_package_task, [package_meta])
    # this is the synchronous task
    return push_package_task(package_meta)
    # return json.dumps(response.id)


# TODO: Remove when AJAX script is in place
@ids_actions.route('/ids/view/push_package/<id>', methods=['GET'])
def push_package_view(id):
    response = push_package(id)
    h.flash_success( _('Object pushed to the DataspaceConnector Catalog.'))
    return toolkit.redirect_to('dataset.read', id=id)


@ids_actions.route('/ids/actions/push_organization/<id>', methods=['GET'])
def push_organization(id):
    organization_meta = toolkit.get_action("organization_show")(None, {"id":id})
    response = toolkit.enqueue_job(push_organization_task, [organization_meta])
    push_organization_task(organization_meta)
    return json.dumps(response.id)


# TODO: Remove when AJAX script is in place
@ids_actions.route('/ids/view/push_organization/<id>', methods=['GET'])
def push_organization_view(id):
    response = push_organization(id)
    h.flash_success( _('Object pushed successfully to Central node, jobId: ') + response)
    return toolkit.redirect_to('organization.read', id=id)

@ids_actions.route('/ids/actions/publish/<id>', methods=['POST'])
def publish_action(id):
    local_connector_resource_api = Connector().get_resource_api()
    c = plugins.toolkit.g
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               }
    dataset = toolkit.get_action('package_show')(context, {'id': id})
    c.pkg_dict = dataset
    contract_meta = request.data
    # create the contract
    contract_id = local_connector_resource_api.create_contract(
        {
            "start": contract_meta.contract_start.isoformat(),
            "end": contract_meta.contract_end.isoformat(),
            "title": contract_meta.title
        }
    )
    # create the rules
    rules = []
    for policy in contract_meta.policies:
        rule = local_connector_resource_api.get_new_policy(policy)
        rule_id = local_connector_resource_api.create_rule({"value": rule})
        rules.append(rule_id)
    # add rules to contract
    local_connector_resource_api.add_rule_to_contract(contract=contract_id, rule=rules)
    resource_id = next((sub for sub in dataset["extras"] if sub['key'] == 'offers'), None)["value"]
    local_connector_resource_api.add_contract_to_resource(resource=resource_id, contract=contract_id)
    extras = dataset["extras"]
    extras.append({"key": "contract", "value": contract_id})
    extras.append({"key": "contract_meta", "value": contract_meta.toJSON()})

    updated_package = toolkit.get_action("package_patch")(context, {"id": id, "extras": extras})





@ids_actions.route('/ids/view/publish/<id>', methods=['GET', 'POST'])
def publish(id, offering_info=None, errors=None):
    c = plugins.toolkit.g
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               }
    dataset = toolkit.get_action('package_show')(context, {'id': id})
    c.pkg_dict = dataset
    c.usage_policies = config.get("ckanext.ids.usage_control_policies")
    c.offering = {}
    c.errors = {}
    if request.method == "POST":
        try:
            contract = Contract(request.form)
            c.offering = contract
            c.errors = contract.errors
            if len(contract.errors) == 0:
                request.data = contract
                publish_action(id)
        except KeyError as e:
            print("there was an error")

    return toolkit.render('package/publish.html',
                          extra_vars={
                              u'pkg_dict': dataset
                          })

@ids_actions.route('/ids/view/contracts/<id>', methods=['GET'])
def contracts(id, offering_info=None, errors=None):
    c = plugins.toolkit.g
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author, 'auth_user_obj': c.userobj,
               }
    dataset = toolkit.get_action('package_show')(context, {'id': id})
    c.pkg_dict = dataset
    contract = json.loads(next((sub for sub in dataset["extras"] if sub['key'] == 'contract_meta'), None)["value"])

    c.contracts = [contract]
    return toolkit.render('package/contracts.html',
                          extra_vars={
                              u'pkg_dict': dataset
                          })

def create_or_get_catalog_id():
    local_connector_resource_api = Connector().get_resource_api()
    title = config.get("app_instance_uuid")
    catalogs = local_connector_resource_api.get_catalogs()
    found = False
    for i, value in enumerate(catalogs["_embedded"]["catalogs"]):
        if value["title"] == title:
            found = True
            catalog_iri = value["_links"]["self"]["href"]
            continue

    if not found:
        catalog = {"title": title}
        catalog_iri = local_connector_resource_api.create_catalog(catalog)
    config.store.update({"ckanext.ids.connector_catalog_iri": catalog_iri})
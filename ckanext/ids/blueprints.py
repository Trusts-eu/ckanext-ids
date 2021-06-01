import json

from flask import Blueprint, jsonify, make_response, request
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
from ckan.common import _, config
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.helpers as h
import ckan.lib.base as base
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
        if field.endswith('url') and len(field) > 3 :
            to_delete.append(field)

    ## these are not needed on the schema so we remove them

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
        "match" : {
            "name": id
        },
        "update": {
            "state": "active"
        }
    }
    try:
        toolkit.get_action("package_revise")(None, revise_package_dict )
    ## ulikely to happen, but just to demonstrate error handling
    except (ValidationError):
        return base.abort(404, _(u'Dataset not found'))
    # redirect tp dataset read page
    return toolkit.redirect_to('dataset.read',
                        id=id)

@ids.route('/dataset/<id>/resources/delete', methods=['DELETE'])
def delete(id):
    return "deleted"

def push_package_task(dataset_dict):
    action= 'package_create'
    push_to_central(data=dataset_dict, action=action)

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

def transform_url(url):
    site_url = toolkit.config.get('ckan.site_url')
    log.info("Transforming url: %s", url)
    log.debug("ckan.site_url is set to: %s", site_url)
    log.debug(url)
    # splitting the url based on the ckan.site_url setting
    resource_url_part= url.split(site_url,1) [1]
    tranformed_url = toolkit.config.get('ckanext.ids.central_node_connector_url') + toolkit.config.get('ckanext.ids.local_node_name') + "/ckan/5000" + resource_url_part
    log.info("URL is now: %s", tranformed_url)
    return tranformed_url

@ids_actions.route('/ids/actions/push_package/<id>', methods=['GET'])
def push_package(id):
    package_meta = toolkit.get_action("package_show")(None, {"id":id})
    for index, resource in enumerate(package_meta['resources']):
        package_meta['resources'][index]['url_type'] = ''
        package_meta['resources'][index]['url'] = transform_url(resource['url'])
    response = toolkit.enqueue_job(push_package_task, [package_meta])
    push_package_task(package_meta)
    return json.dumps(response.id)

## TODO: Remove when AJAX script is in place
@ids_actions.route('/ids/view/push_package/<id>', methods=['GET'])
def push_package_view(id):
    response = push_package(id)
    h.flash_success( _('Object pushed successfuly to Central node, jobId: ') + response)
    return toolkit.redirect_to('dataset.read', id=id)

@ids_actions.route('/ids/actions/push_organization/<id>', methods=['GET'])
def push_organization(id):
    organization_meta = toolkit.get_action("organization_show")(None, {"id":id})
    response = toolkit.enqueue_job(push_organization_task, [organization_meta])
    push_organization_task(organization_meta)
    return json.dumps(response.id)

## TODO: Remove when AJAX script is in place
@ids_actions.route('/ids/view/push_organization/<id>', methods=['GET'])
def push_organization_view(id):
    response = push_organization(id)
    h.flash_success( _('Object pushed successfuly to Central node, jobId: ') + response)
    return toolkit.redirect_to('organization.read', id=id)
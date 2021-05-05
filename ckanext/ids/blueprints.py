import json

from flask import Blueprint, jsonify, make_response, request
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.helpers as h
import ckan.lib.base as base
from ckan.common import _
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

def print_test(msg):
    print(msg)
#    push_to_ckan(dataset_dict=msg)

# def push_to_ckan(dataset_dict, node_url=''):
#     data_string = urllib.quote(json.dumps(dataset_dict))
#     # We'll use the package_create function to create a new dataset.
#     url = node_url + 'api/action/package_create'
#     url = 'https://google.com/'
#     request = urllib2.Request(url)
#     # Creating a dataset requires an authorization header.
#     # Replace *** with your API key, from your user account on the CKAN site
#     # that you're creating the dataset on.
#     request.add_header('Authorization', '***')
#     # Make the HTTP request.
#     response = urllib2.urlopen(request, data_string)
#     assert response.code == 200
#     # Use the json module to load CKAN's response into a dictionary.
#     response_dict = json.loads(response.read())
#     assert response_dict['success'] is True
#     # package_create returns the created package as its result.

@ids_actions.route('/ids/actions/push/<id>', methods=['GET'])
def push(id):
    package_meta = toolkit.get_action("package_show")(None, {"id":id})
    response = toolkit.enqueue_job(print_test, [package_meta])
    print_test(package_meta)
    return json.dumps(response.id)

## TODO: Remove when AJAX script is in place
@ids_actions.route('/ids/view/push/<id>', methods=['GET'])
def push_view(id):
    response = push(id)
    h.flash_success( _('Object pushed successfuly to Central node, jobId: ') + response)
    return toolkit.redirect_to('dataset.read', id=id)

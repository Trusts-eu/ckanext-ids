import json

from flask import Blueprint, jsonify, make_response, request
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
from werkzeug.datastructures import ImmutableMultiDict

tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

ids = Blueprint(
    'ids',
    __name__
)

ids_actions = Blueprint(
    'ids_actions',
    __name__
)

@ids.route('/dataset/<id>/resources/create', methods=['POST'])
def create(id):
    data = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(request.form))))
    data['package_id'] = id
    del data['clear_upload']
    del data['save']
    resources = []
    for file in request.files:
        resource = data.copy()
        files = ImmutableMultiDict([(file, request.files[file])])
        resource.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(files)))))
        resource['upload'] = resource[file]
        del resource[file]
        resources.append(resource)

    for resource in resources:
        toolkit.get_action('resource_create')(None, resource)

    return toolkit.redirect_to('dataset.read',
                        id=id)

@ids.route('/dataset/<id>/resources/delete', methods=['DELETE'])
def delete(id):
    return "deleted"

def print_test(msg):
    print(msg)

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
    return toolkit.redirect_to('dataset.read', id=id)

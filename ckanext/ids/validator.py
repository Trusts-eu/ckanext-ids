from six.moves.urllib.parse import urlparse
from ckan.logic import validators
import string
from ckan.common import _
from ckanext.scheming.validation import register_validator, scheming_validator

@register_validator
def trusts_url_validator(key, data, errors, context):
    ''' Checks that the provided value (if it is present) is a valid URL '''

    url = data.get(key, None)
    if not url:
        return

    try:
        pieces = urlparse(url)
        if all([pieces.scheme, pieces.netloc]) and \
                set(pieces.netloc) <= set(string.ascii_letters + string.digits + '-.:') and \
                pieces.scheme in ['http', 'https']:
            return
    except ValueError:
        # url is invalid
        pass

    errors[key].append(_('Please provide a valid URL'))

    # Custom Activities

_object_id_validators = {
    'pushed to dataspace connector': validators.package_id_exists,
    'created contract': validators.package_id_exists
}

def object_id_validator(key, activity_dict, errors, context):
    '''Validate the 'object_id' value of an activity_dict.
    This wraps ckan.logic.validators.object_id_validator to support additional
    object types
    '''
    activity_type = activity_dict[('activity_type',)]
    if activity_type in _object_id_validators:
        object_id = activity_dict[('object_id',)]
        return _object_id_validators[activity_type](object_id, context)
    return validators.object_id_validator(key, activity_dict, errors, context)


def activity_type_exists(activity_type):
    '''Wrap ckan.logic.validators.activity_type_exists to support additional
    activity stream types
    '''
    if activity_type in _object_id_validators:
        return activity_type
    return validators.activity_type_exists(activity_type)
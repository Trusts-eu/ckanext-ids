from six.moves.urllib.parse import urlparse
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
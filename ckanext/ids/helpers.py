import logging
import json
from ckan.common import is_flask_request

from ckan.common import _, c, request

log = logging.getLogger(__name__)


def check_if_contract_offer_exists(id):
    return True

def string_to_json(json_string):
    return json.loads(json_string)

def get_facet_items_dict(
        facet, search_facets=None, limit=None, exclude_active=False):
    '''Return the list of unselected facet items for the given facet, sorted
    by count.
    Returns the list of unselected facet contraints or facet items (e.g. tag
    names like "russian" or "tolstoy") for the given search facet (e.g.
    "tags"), sorted by facet item count (i.e. the number of search results that
    match each facet item).
    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.
    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets(c.search_facets in Pylons)
    limit -- the max. number of facet items to return.
    exclude_active -- only return unselected facets.
    '''
    if search_facets is None:
        search_facets = getattr(c, u'search_facets', None)

    if not search_facets or not search_facets.get(
            facet, {}).get('items'):
        return []
    facets = []
    for facet_item in search_facets.get(facet)['items']:
        if not len(facet_item['name'].strip()):
            continue
        params_items = request.params.items(multi=True) \
            if is_flask_request() else request.params.items()
        if not (facet, facet_item['name']) in params_items:
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    # Sort descendingly by count and ascendingly by case-sensitive display name
    facets.sort(key=lambda it: (-it['count'], it['display_name'].lower()))
    if hasattr(c, 'search_facets_limits'):
        if c.search_facets_limits and limit is None:
            limit = c.search_facets_limits.get(facet)
    # zero treated as infinite for hysterical raisins
    if limit is not None and limit > 0:
        return facets[:limit]
    return facets


def has_more_facets(facet, search_facets, limit=None, exclude_active=False):
    '''
    Returns True if there are more facet items for the given facet than the
    limit.
    Reads the complete list of facet items for the given facet from
    c.search_facets, and filters out the facet items that the user has already
    selected.
    Arguments:
    facet -- the name of the facet to filter.
    search_facets -- dict with search facets(c.search_facets in Pylons)
    limit -- the max. number of facet items.
    exclude_active -- only return unselected facets.
    '''
    facets = []
    for facet_item in search_facets.get(facet)['items']:
        if not len(facet_item['name'].strip()):
            continue
        params_items = request.params.items(multi=True) \
            if is_flask_request() else request.params.items()
        if not (facet, facet_item['name']) in params_items:
            facets.append(dict(active=False, **facet_item))
        elif not exclude_active:
            facets.append(dict(active=True, **facet_item))
    if hasattr(c, 'search_facets_limits'):
        if c.search_facets_limits and limit is None:
            limit = c.search_facets_limits.get(facet)
    if limit is not None and len(facets) > limit:
        return True
    return False
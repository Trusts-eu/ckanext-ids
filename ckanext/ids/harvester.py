import json

from six.moves.urllib.parse import urlencode
from urllib3.contrib import pyopenssl
import requests
from requests.exceptions import HTTPError, RequestException
import urllib.parse as urlparse
from urllib.parse import parse_qs
import ckan.plugins.toolkit as toolkit
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

import logging
log = logging.getLogger(__name__)


class TrustsHarvester(CKANHarvester):
    '''
    A Harvester for CKAN instances. Extends the default from ckan-harvest extension
    '''

    def flatten_query(self, query_list):
        flatten = dict()
        for key, value in query_list:
            flatten[key] = value

        return flatten

    def _get_content(self, url):

        headers = {}
        api_key = self.config.get('api_key')
        if api_key:
            headers['Authorization'] = api_key

        pyopenssl.inject_into_urllib3()
        parsed = urlparse.urlparse(url)
        data = self.flatten_query(urlparse.parse_qsl(parsed.query))
        url_parsed = parsed.scheme + "://" + parsed.netloc + parsed.path
        try:
            http_request = requests.post(url_parsed, json=data, headers=headers)
        except HTTPError as e:
            raise ContentFetchError('HTTP error: %s %s' % (e.response.status_code, e.request.url))
        except RequestException as e:
            raise ContentFetchError('Request error: %s' % e)
        except Exception as e:
            raise ContentFetchError('HTTP general exception: %s' % e)
        return http_request.text

    def _search_for_datasets(self, remote_ckan_base_url, fq_terms=None):
        '''Does a dataset search on a remote CKAN and returns the results.
        Deals with paging to return all the results, not just the first page.
        '''

        base_search_url = remote_ckan_base_url + self._get_search_api_offset()
        params = {'rows': '100', 'start': '0', 'include_private': self.config.get('include_private', 'true')}
        # There is the worry that datasets will be changed whilst we are paging
        # through them.
        # * In SOLR 4.7 there is a cursor, but not using that yet
        #   because few CKANs are running that version yet.
        # * However we sort, then new names added or removed before the current
        #   page would cause existing names on the next page to be missed or
        #   double counted.
        # * Another approach might be to sort by metadata_modified and always
        #   ask for changes since (and including) the date of the last item of
        #   the day before. However if the entire page is of the exact same
        #   time, then you end up in an infinite loop asking for the same page.
        # * We choose a balanced approach of sorting by ID, which means
        #   datasets are only missed if some are removed, which is far less
        #   likely than any being added. If some are missed then it is assumed
        #   they will harvested the next time anyway. When datasets are added,
        #   we are at risk of seeing datasets twice in the paging, so we detect
        #   and remove any duplicates.
        params['sort'] = 'id asc'
        if fq_terms:
            params['fq'] = ' '.join(fq_terms)

        pkg_dicts = []
        pkg_ids = set()
        previous_content = None
        while True:
            url = base_search_url + '?' + urlencode(params)
            log.debug('Searching for CKAN datasets: %s', url)
            try:
                content = self._get_content(url)
            except ContentFetchError as e:
                raise SearchError(
                    'Error sending request to search remote '
                    'CKAN instance %s using URL %r. Error: %s' %
                    (remote_ckan_base_url, url, e))

            if previous_content and content == previous_content:
                raise SearchError('The paging doesn\'t seem to work. URL: %s' %
                                  url)
            try:
                response_dict = json.loads(content)
            except ValueError:
                raise SearchError('Response from remote CKAN was not JSON: %r'
                                  % content)
            try:
                pkg_dicts_page = response_dict.get('result', {}).get('results',
                                                                     [])
            except ValueError:
                raise SearchError('Response JSON did not contain '
                                  'result/results: %r' % response_dict)

            # Weed out any datasets found on previous pages (should datasets be
            # changing while we page)
            ids_in_page = set(p['id'] for p in pkg_dicts_page)
            duplicate_ids = ids_in_page & pkg_ids
            if duplicate_ids:
                pkg_dicts_page = [p for p in pkg_dicts_page
                                  if p['id'] not in duplicate_ids]
            pkg_ids |= ids_in_page

            pkg_dicts.extend(pkg_dicts_page)

            if len(pkg_dicts_page) == 0:
                break

            params['start'] = str(int(params['start']) + int(params['rows']))

        return pkg_dicts

    def modify_package_dict(self, package_dict, harvest_object):

        for index, resource in enumerate(package_dict['resources']):
            package_dict['resources'][index]['url'] = self.transform_url(resource['url'])

        return package_dict

    def transform_url(self, url):
        trusted_connector_port = "8282"
        site_url = toolkit.config.get('ckan.site_url')
        log.info("Transforming url: %s", url)
        log.debug("ckan.site_url is set to: %s", site_url)
        parsed_site_url = urlparse.urlsplit(site_url)
        localhost = parsed_site_url.scheme + "://" + parsed_site_url.hostname + ":" + trusted_connector_port
        log.debug("Local trusted connector is on : %s", localhost)
        resource_path = urlparse.urlsplit(url)
        log.debug("Resource path: %s", resource_path.path)
        # splitting the url based on the ckan.site_url setting
        tranformed_url = localhost + resource_path.path
        log.info("URL is now: %s", tranformed_url)
        return tranformed_url


class ContentFetchError(Exception):
    pass


class ContentNotFoundError(ContentFetchError):
    pass


class RemoteResourceError(Exception):
    pass


class SearchError(Exception):
    pass

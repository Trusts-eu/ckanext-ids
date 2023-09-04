import inspect
import json
import logging
import os

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import config
import ckan.model as model
from ckan.lib.plugins import DefaultTranslation
import ckanext.ids.blueprints as blueprints
import ckanext.ids.swagger as swagger
import ckanext.ids.validator as validator
from ckanext.ids.metadatabroker.client import broker_package_search, strip_scheme
from collections import OrderedDict, Counter
from typing import Any


#dtheiler start
from ckanext.ids.recomm.recomm import recomm_recomm_datasets_homepage
from ckanext.ids.recomm.recomm import recomm_recomm_services_homepage
from ckanext.ids.recomm.recomm import recomm_recomm_applications_homepage

from ckanext.ids.recomm.recomm import recomm_recomm_applications_sidebar
from ckanext.ids.recomm.recomm import recomm_recomm_datasets_sidebar
from ckanext.ids.recomm.recomm import recomm_recomm_services_sidebar
#dtheiler end

from ckanext.ids.helpers import check_if_contract_offer_exists, has_more_facets, get_facet_items_dict, string_to_json
from ckanext.scheming.helpers import scheming_get_schema, scheming_field_by_name
from ckanext.vocabularies.helpers import skos_choices_sparql_helper, skos_choices_get_label_by_value

## Take a look in https://github.com/ckan/ckan/issues/5865 and https://github.com/ckan/ckan/blob/master/ckanext/activity/logic/validators.py
#from ckan.logic import validators as core_validators

# ToDo make sure this logger is set higher
log = logging.getLogger("ckanext")

#dtheiler start
def recomm_datasets_homepage(count):
    return recomm_recomm_datasets_homepage(count)

def recomm_services_homepage(count):
    return recomm_recomm_services_homepage(count)

def recomm_applications_homepage(count):
    return recomm_recomm_applications_homepage(count)
    
def recomm_applications_sidebar(entity, count):
    return recomm_recomm_applications_sidebar(entity, count)
    
def recomm_datasets_sidebar(entity, count):
    return recomm_recomm_datasets_sidebar(entity, count)

def recomm_services_sidebar(entity, count):
    return recomm_recomm_services_sidebar(entity, count)    
#dtheiler end

class IdsPlugin(plugins.SingletonPlugin, DefaultTranslation):
    log.debug("\n................ Plugin Init 5................\n+")
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IValidators)

    plugins.implements(plugins.ITemplateHelpers)

    def get_helpers(self):
        return {
            'ckanext_ids_check_if_contract_offer_exists': check_if_contract_offer_exists,
            'get_facet_items_dict': get_facet_items_dict,
            'has_more_facets': has_more_facets,
            'string_to_json': string_to_json
            }
    
    def get_validators(self):
        return {
            "trusts_url_validator": validator.trusts_url_validator,
            "object_id_validator": validator.object_id_validator,
            "activity_type_exists": validator.activity_type_exists
        }

    from ckanext.ids.model import setup as db_setup


    db_setup()

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets',
                             'ckanext-ids')

        #core_validators.object_id_validators['created contract'] = core_validators.package_id_exists
        #core_validators.object_id_validators['pushed to dataspace connector'] = core_validators.package_id_exists

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        is_boolean = toolkit.get_validator('boolean_validator')

        schema.update({
            # This is an existing CKAN core configuration option, we are just
            # making it available to be editable at runtime
            'ckan.search.show_all_types': [ignore_missing, is_boolean],
            'ckanext.ids.connector_catalog_iri': [ignore_missing],
            'ckanext.ids.usage_control_policies': [ignore_missing]

        })

        return schema
    # before rendering organization view
    def before_view(self, organization):
        log.debug("\n................ Before View ................\n+")
        data_application = {
            'fq': '+type:application +organization:' + organization['name'],
            'include_private': True,
            'ext_include_broker_results': False
        }
        application_search = toolkit.get_action("package_search")(None,
                                                                  data_application)
        data_service = {
            'fq': '+type:service +organization:' + organization['name'],
            'include_private': True,
            'ext_include_broker_results': False
        }
        service_search = toolkit.get_action("package_search")(None,
                                                              data_service)
        data_dataset = {
            'fq': '+type:dataset +organization:' + organization['name'],
            'include_private': True,
            'ext_include_broker_results': False
        }
        dataset_search = toolkit.get_action("package_search")(None,
                                                              data_dataset)
        organization['application_count'] = application_search['count']
        organization['service_count'] = service_search['count']
        organization['dataset_count'] = dataset_search['count']
        return organization

    # IBlueprint
    plugins.implements(plugins.IBlueprint)

    def get_blueprint(self):
        return [blueprints.ids_actions]
        

# The following code is an example of how we can implement a plugin that performs an action on a specific event.
# The event is a package read event, show it will be activated whenever a package is read ie. opening the URL of a
# package on the browser. The plugin implements for this the IPackageController. When this is activated, it enqueues a
# background job that will execute the print_test method asynchronously and also executes the same method synchronously.
# If this plugin is enabled, you will see the message 'This is a synchronous test' on the output of the debugging server
# whenever a package is read. The job queue can be seen if you issue the command
# 'ckan -c /etc/ckan/debugging.ini jobs list'
# You can run a worker that will start picking up jobs from the queue list with the command
# 'ckan -c /etc/ckan/debugging.ini jobs worker'
# Then on your terminal you will see the messages produced by the job.


class IdsDummyJobPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)

    def read(self, entity):
        toolkit.enqueue_job(blueprints.print_test, [u'This is an async test'])
        blueprints.print_test('This is a synchronous test')

        return entity


def assert_config():
    configuration_keys = {
        'ckanext.ids.trusts_local_dataspace_connector_url',
        'ckanext.ids.trusts_local_dataspace_connector_username',
        'ckanext.ids.trusts_local_dataspace_connector_password',
        'ckan.site_url'
    }
    for key in configuration_keys:
        try:
            assert toolkit.config.get(key) is not None
        except AssertionError:
            raise EnvironmentError(
                'Configuration property {0} was not set. '
                'Please fix your configuration.'.format(
                    key))


# used to load the policy templates from a local json file. A default is already provided.
# For now the name and position of the file is hardcoded
def load_usage_control_policies():
    url = "ckanext.ids:usage_control.json"
    module, file_name = url.split(':', 1)
    try:
        m = __import__(module, fromlist=[''])
    except ImportError:
        return

    p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
    if os.path.exists(p):
        with open(p) as schema_file:
            return json.load(schema_file)


def transform_usage_control_policies(policies):
    for policy in policies["policy_templates"]:
        for field in policy["fields"]:
            field["field_name"] = policy["type"] + "_" + field["field_name"]
            try:
                field["form_attrs"]["disabled"] = ""
            except KeyError:
                field["form_attrs"] = {"disabled": ""}


def get_usage_control_policies():
    usage_control_policies = load_usage_control_policies()
    transform_usage_control_policies(usage_control_policies)
    return usage_control_policies


# TODO: hack licenses till ckan images gets updated to at least 2.10.1

def license_list():
    '''Return the list of licenses available for datasets on the site.

    :rtype: list of dictionaries

    '''
    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licenses = [license_dictize(l) for l in licenses]
    return licenses

def license_dictize(license) -> dict[str, Any]:
    data = license._data.copy()
    if 'date_created' in data:
        value = data['date_created']
        value = value.isoformat()
        data['date_created'] = value
    return data


def dictionize_licenses():
    licenses_dict = {}
    for license in license_list():
        licenses_dict[license["url"]] = license
    return licenses_dict

# end of hack


class IdsResourcesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)
    assert_config()
    blueprints.create_or_get_catalog_id()
    # fixing the names in the policy templates and adding some default options
    config.store.update(
        {"ckanext.ids.usage_control_policies": get_usage_control_policies(),
         "ckanext.ids.licenses": dictionize_licenses()})

    def get_blueprint(self):
        return [blueprints.ids, swagger.swaggerui_blueprint]

    plugins.implements(plugins.IFacets, inherit=True)

    # Here we define the facets fields that will be added when a package search is triggered.
    def dataset_facets(self, facets_dict, package_type):
        new_facets_dict = OrderedDict()
        new_facets_dict["license_id"] = plugins.toolkit._("License")
        new_facets_dict["theme"] = plugins.toolkit._("Theme")
        new_facets_dict["TimeFrame"] = plugins.toolkit._("Time Frame")

        return new_facets_dict

    plugins.implements(plugins.IPackageController, inherit=True)

    def after_dataset_delete(self, context, pkg_dict):
        package_meta = toolkit.get_action("package_show")(None, {
            "id": pkg_dict["id"]})
        blueprints.delete_from_dataspace_connector(package_meta)

    def before_dataset_search(self, search_params):
        return search_params

    def after_dataset_search(self, search_results, search_params):
        context = plugins.toolkit.g

        if context.view == "search":
            results_from_broker = self.retrieve_results_from_broker(search_params)
            if len(results_from_broker) > 0:
               search_results["results"] = results_from_broker["results"]
               search_results["count"] = results_from_broker["count"]
               search_results["facets"] = results_from_broker["facets"]
               search_results["search_facets"] = self.retrieve_facet_labels(results_from_broker["search_facets"])
        #TODO: check if this is still needed, for now it does not work on CKAN 2.10.0 sss
        #if context.view == "read":
        #    results_from_broker = self.retrieve_results_from_broker(search_params)
        #    if len(results_from_broker) > 0:
        #        search_results["results"].extend(results_from_broker["results"])
        #        search_results["count"] += results_from_broker["count"]
        #        search_results["facets"] = self.merge_facets(search_results["facets"], results_from_broker["facets"])
        #        search_results["search_facets"] = self.merge_search_facets(search_results["search_facets"], results_from_broker["search_facets"])
        else:
            pass

        if "ext_include_tracking" in search_params["extras"]:
            if toolkit.asbool(search_params["extras"]["ext_include_tracking"]):
                for result in search_results["results"]:
                    result['tracking_summary'] = (
                    model.TrackingSummary.get_for_package(result['id']))

        return search_results

    def retrieve_results_from_broker(self, search_params):
        log.debug("\n................ After Search ................\n+")
        # log.debug("\n\nParams------------------------------------------>")
        # log.debug(json.dumps(search_params, indent=2))
        # log.debug("\n\nResults----------------------------------------->")
        # log.debug(json.dumps(search_results, indent=2))

        start = search_params.get("start", 0)
        limit = search_params.get("rows", 20)
        search_query = search_params.get("q", None)

        # The parameters include organizations, we remove this
        fqset = search_params.get("fq", None)
        if fqset is not None:
            fq2 = []
            for f in fqset:
                fq2.extend([x for x in f.split()
                                     if "+organization" not in x])

            fqset = fq2
            fqset.sort()

        fq = tuple(fqset)

        results_from_broker = broker_package_search(q=search_query,
                                                    fq=fq,
                                                    start_offset=start,
                                                    limit=limit,
                                                    facet_fields=search_params.get("facet.field", None))

        # log.debug(".\n\n\n---BROKER SEARCH RESULTS ARE   ")
        # log.debug(json.dumps([x["name"] for x in  results_from_broker],
        #                     indent=1))
        # log.debug(".\n\n---------------------------:)\n\n ")
        return results_from_broker

    def merge_facets(self, solr_results: dict, broker_results: dict):
        for facet in broker_results.keys():
            if facet in solr_results.keys():
                solr_results[facet] = dict(Counter(broker_results[facet]) + Counter(solr_results[facet]))
            else:
                solr_results[facet] = broker_results[facet]
        return solr_results

    def merge_search_facets(self, solr_results: dict, broker_results: dict):
        for facet in broker_results.keys():
            if facet in solr_results.keys():
                solr_results_facet_item_names = [item['name'] for item in solr_results[facet]["items"]]
                for broker_item in broker_results[facet]["items"]:
                    if broker_item["name"] in solr_results_facet_item_names:
                        index = solr_results_facet_item_names.index(broker_item["name"])
                        solr_results[facet]["items"][index]["count"] += broker_item["count"]
                    else:
                        solr_results[facet]["items"].append(broker_item)
            else:
                solr_results[facet] = broker_results[facet]
        solr_results = self.retrieve_facet_labels(solr_results)
        return solr_results

    def retrieve_facet_labels(self, results: dict):
        dataset_schema = scheming_get_schema("dataset", "dataset", True)
        for facet_key in results:
            if facet_key == "license_id":
                results["license_id"] = self.retrieve_facet_license_labels(results)["license_id"]
            else:
                schema_field = scheming_field_by_name(dataset_schema["dataset_fields"], facet_key)
                if schema_field["choices_helper"] == "skos_vocabulary_helper":
                    skos_choices = skos_choices_sparql_helper(schema_field)
                    for facet_item_index, facet_item in enumerate(results[facet_key]["items"]):
                        display_name = skos_choices_get_label_by_value(skos_choices, facet_item["name"])
                        results[facet_key]["items"][facet_item_index]["display_name"] = display_name

        return results

    def retrieve_facet_license_labels(self, solr_results: dict):
        licenses = config.get("ckanext.ids.licenses")
        for facet_item_index, facet_item in enumerate(solr_results["license_id"]["items"]):
            display_name = None
            if facet_item["name"].find("http") != -1:
                if facet_item["name"].find("cc-zero") > 0 :
                    display_name = "CC0 1.0"
                else:
                    try:
                        display_name = licenses[facet_item["name"]]["title"]
                    except KeyError:
                        display_name = "Old license url"

                    solr_results["license_id"]["items"][facet_item_index]["display_name"] = display_name
        return solr_results


class TrustsRecommenderPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IConfigurer, inherit=True)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates_recommender')
    def get_helpers(self):
        return {
            'ckanext_ids_recomm_datasets_homepage': recomm_datasets_homepage,
            'ckanext_ids_recomm_services_homepage': recomm_services_homepage,
            'ckanext_ids_recomm_applications_homepage': recomm_applications_homepage,
            'ckanext_ids_recomm_applications_sidebar': recomm_applications_sidebar,
            'ckanext_ids_recomm_datasets_sidebar': recomm_datasets_sidebar,
            'ckanext_ids_recomm_services_sidebar': recomm_services_sidebar
        }
    # IBlueprint
    plugins.implements(plugins.IBlueprint)

    def get_blueprint(self):
        return [blueprints.trusts_recommender]


class TrustsBlockchainPlugin(plugins.SingletonPlugin):
    pass


class DevPlugin(plugins.SingletonPlugin):
    """Development plugin.
    This plugin provides:
    - Start remote debugger (if correct library is present) during update_config call
    """

    plugins.implements(plugins.IConfigurer, inherit=True)

    def update_config(self, config):
        self._start_debug_client(config)

    def _start_debug_client(self, config):
        try:
            log.info("Trying to load the pydevd library.")
            import pydevd
        except ImportError:
            log.error("Failed to load the pydedv library.")
            pass

        host_ip = config.get('debug.remote.host.ip', '172.20.0.1')
        host_port = config.get('debug.remote.host.port', '64342')
        stdout = toolkit.asbool(config.get('debug.remote.stdout_to_server', 'True'))
        stderr = toolkit.asbool(config.get('debug.remote.stderr_to_server', 'True'))
        suspend = toolkit.asbool(config.get('debug.remote.suspend', 'False'))

        try:
            log.info("Initiating remote debugging session to {}:{}".format(host_ip, host_port))
            pydevd.settrace(host_ip, port=int(host_port), stdoutToServer=stdout, stderrToServer=stderr, suspend=suspend)
            log.info("Successfully started debugging session...")
        except NameError:
            log.warning("debug.enabled set to True, but pydevd is missing.")
        except SystemExit:
            log.warning("Failed to connect to debug server; is it started?")

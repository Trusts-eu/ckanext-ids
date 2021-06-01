import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
import ckanext.ids.blueprints as blueprints


class IdsPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.ITranslation)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets',
            'ckanext-ids')

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        is_boolean = toolkit.get_validator('boolean_validator')

        schema.update({
            # This is an existing CKAN core configuration option, we are just
            # making it available to be editable at runtime
            'ckan.search.show_all_types': [ignore_missing, is_boolean]
        })

        return schema

    def before_view(self, pkg_dict):
        data_application = {
            'fq': '+type:application +organization:' + pkg_dict['name'],
            'include_private': True
        }
        application_search = toolkit.get_action("package_search")(None, data_application)
        data_service = {
            'fq': '+type:service +organization:' + pkg_dict['name'],
            'include_private': True
        }
        service_search = toolkit.get_action("package_search")(None, data_service)
        data_dataset = {
            'fq': '+type:dataset +organization:' + pkg_dict['name'],
            'include_private': True
        }
        dataset_search = toolkit.get_action("package_search")(None, data_dataset)
        pkg_dict['application_count'] = application_search['count']
        pkg_dict['service_count'] = service_search['count']
        pkg_dict['dataset_count'] = dataset_search['count']
        return pkg_dict

    # IBlueprint
    plugins.implements(plugins.IBlueprint)

    def get_blueprint(self):
        return [blueprints.ids_actions]
        #return entity

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
    configuration_keys = {'ckanext.ids.central_node_url', 'ckanext.ids.central_node_connector_url', 'ckanext.ids.local_node_name', 'ckan.site_url'}
    for key in configuration_keys:
        try:
            assert toolkit.config.get(key) is not None
        except AssertionError:
            raise EnvironmentError('Configuration property {0} was not set. Please fix your configuration.'.format(key))
        try:
            assert toolkit.config.get(key) is not ''
        except AssertionError:
            raise EnvironmentError('Configuration property {0} was set but was empty string. Please fix your configuration.'.format(key))


class IdsResourcesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IBlueprint)
    assert_config()

    def get_blueprint(self):
        return [blueprints.ids]

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class IdsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('assets',
            'ids')

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        is_positive_integer = toolkit.get_validator('is_positive_integer')
        is_boolean = toolkit.get_validator('boolean_validator')

        schema.update({
            # This is an existing CKAN core configuration option, we are just
            # making it available to be editable at runtime
            'ckan.search.show_all_types': [ignore_missing, is_boolean]
        })

        return schema
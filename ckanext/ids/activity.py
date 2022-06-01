from ckan import model
import ckan.plugins.toolkit as toolkit


def create_pushed_to_dataspace_connector_activity(context, pkg_id):
    """
    Log a 'pushed to dataspace connector' activity in the activity stream
    """
    user = context['user']
    user_id = None
    user_by_name = model.User.by_name(user)
    if user_by_name is not None:
        user_id = user_by_name.id

    package = toolkit.get_action('package_show')(context.copy(), {'id': pkg_id})

    activity_dict = {
        'activity_type': 'pushed to dataspace connector',
        'user_id': user_id,
        'object_id': pkg_id,
        'data':
            {'package': package}
    }

    activity_create_context = {
        'model': model,
        'user': user_id or user,
        'defer_commit': False,
        'ignore_auth': True,
    }

    create_activity = toolkit.get_action('activity_create')
    create_activity(activity_create_context, activity_dict)


def create_created_contract_activity(context, pkg_id):
    """
    Log a 'pushed to dataspace connector' activity in the activity stream
    """
    user = context['user']
    user_id = None
    user_by_name = model.User.by_name(user)
    if user_by_name is not None:
        user_id = user_by_name.id
    package = toolkit.get_action('package_show')(context.copy(), {'id': pkg_id})
    activity_dict = {
        'activity_type': 'created contract',
        'user_id': user_id,
        'object_id': pkg_id,
        'data':
            {'package': package}
    }
    activity_create_context = {
        'model': model,
        'user': user_id or user,
        'defer_commit': False,
        'ignore_auth': True,
    }
    create_activity = toolkit.get_action('activity_create')
    create_activity(activity_create_context, activity_dict)

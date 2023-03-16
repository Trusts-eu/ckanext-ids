[![Tests](https://github.com/semantic-web-company/ckanext-ids/workflows/Tests/badge.svg?branch=main)](https://github.com/semantic-web-company/ckanext-ids/actions)

# ckanext-ids

**TODO:** Put a description of your extension here:  What does it do? What features does it have? Consider including some screenshots or embedding a video!


## Requirements

**TODO:** For example, you might want to mention here which versions of CKAN this
extension works with.

If your extension works across different versions you can add the following table:

Compatibility with core CKAN versions:

| CKAN version    | Compatible? |
| --------------- |-------------|
| 2.6 and earlier | not tested  |
| 2.7             | not tested  |
| 2.8             | not tested  |
| 2.9             | tested      |

Suggested values:

* "yes"
* "not tested" - I can't think of a reason why it wouldn't work
* "not yet" - there is an intention to get it working
* "no"


## Installation

**TODO:** Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-ids:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate


2. Clone the source and install it on the virtualenv

    git clone https://github.com/semantic-web-company/ckanext-ids.git
    cd ckanext-ids
    pip install -e . 
    pip install -r requirements.txt
   


3. Add `ids` and `ids_dummy to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Config settings

    # The URL of the local dataspace connector
    ckanext.ids.trusts_local_dataspace_connector_url = http://localhost:8089
    # The username of the local dataspace connector
    ckanext.ids.trusts_local_dataspace_connector_username = admin
    # The password of the local dataspace connector
    ckanext.ids.trusts_local_dataspace_connector_password = password


## Developer installation

To install ckanext-ids for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/semantic-web-company/ckanext-ids.git
    cd ckanext-ids
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## Releasing a new version of ckanext-ids

If ckanext-ids should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

        twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)

## Funding
This code was created as part of project TRUSTS: Trusted secure data sharing space.

This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement [No 871481](https://cordis.europa.eu/project/id/871481).

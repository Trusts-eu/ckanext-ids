import datetime
import json
import logging

import ckan.lib.helpers as h
import pytz
from ckan.common import _, config


class Contract:
    pkg_id: None
    contract_start = None
    contract_end = None
    contract_iri: None
    title: None
    rule_iris: []
    errors: {}
    policies: []

    def __init__(self, contract_data):
        """
        contract_data is a dict that must contain the following keys:
         `pkg_id` : the id of the ckan package
         `title`  : the title of the contract
         `contract_start_date`  : date of start of contract  iso
         `contract_start_time`  : date of start of contract  iso format
         `contract_start_tz`    : timezone of start, recongizable by pytz
         `contract_end_date`  : date of end of contract  iso
         `contract_end_time`  : date of end of contract  iso format
         `contract_end_tz`    : timezone of end, recongizable by pytz
         `{POLICY_TYPE}'   : the key itself should be one of the types in
                             the `ckanext/ids/usage_control.json` file

        """
        #print("\n\n---------------------------------")
        #print(json.dumps(contract_data,indent=1))
        #print("\n---------------------------------")
        if "pkg_id" in contract_data:
            self.pkg_id = contract_data["pkg_id"]
        else:
            print("No pkg_id was founnd... why?")
            raise KeyError
        if "title" in contract_data:
            self.title = contract_data["title"]
        else:
            self.title = None
        self.errors = {
                        "contract_start_date": [],
                        "contract_start_time": [],
                        "contract_start_tz": [],
                        "contract_end_date": [],
                        "contract_end_time": [],
                        "contract_end_tz": [],
                        }
        self.contract_start = self.validate_date_inputs("contract_start",
                                                        contract_data,
                                                        self.errors)
        print("validated start date")
        self.contract_end = self.validate_date_inputs("contract_end",
                                                      contract_data,
                                                      self.errors)
        print("validated end date")
        self.policies = self.validate_policies(contract_data, self.errors)
        self.errors = {key:val
                       for key, val
                       in self.errors.items()
                       if len(val)}

    def converter(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        else:
            return o.__dict__

    def toJSON(self):
        return json.dumps(self, default=self.converter,
                      sort_keys=True, indent=4)

    def validate_policies(self, data, errors):
        policies_schema = config.get("ckanext.ids.usage_control_policies")
        policies = []
        for policy_template in policies_schema["policy_templates"]:
            policy_type = policy_template["type"]
            if data.get(policy_type) is None:
                continue
            policy = {
                "type": policy_type
            }
            for field in policy_template["fields"]:
                errors[field["field_name"]] = []
                original_field_name = field["field_name"].split(policy_type + "_", 1)[1]
                try:
                    value = data.get(field["field_name"])
                    if value is None:
                        raise ValueError
                    policy[original_field_name] = value
                except Exception:
                    error_message = policy_type + " was selected, " + original_field_name + " is required."
                    errors[field["field_name"]].append(error_message)
            policies.append(policy)
        if len(policies) == 0:
            errors["policies"] = ["None of the policies was selected, please choose one of the available."]
        return policies

    def validate_date_inputs(self, key, data, errors):
        date_error = _('Date format incorrect')
        time_error = _('Time format incorrect')

        date = None

        def get_input(suffix):
            inpt = key + '_' + suffix
            key_value = data.get(inpt)

            return inpt, key_value

        date_key, value = get_input('date')
        value_full = ''

        if value:
            try:
                value_full = value
                date = h.date_str_to_datetime(value)
            except (TypeError, ValueError) as e:
                errors[date_key].append(date_error)
        else:
            errors[date_key].append(_('Date is required.'))

        time_key, value = get_input('time')
        if value:
            if not value_full:
                errors[date_key].append(
                    _('Date is required when a time is provided'))
            else:
                try:
                    value_full += 'T' + value
                    date = h.date_str_to_datetime(value_full)
                except (TypeError, ValueError) as e:
                    errors[time_key].append(time_error)
        else:
            errors[time_key].append(_('Time is required.'))

        tz_key, value = get_input('tz')
        if value:
            if value not in pytz.all_timezones:
                errors[tz_key].append('Invalid timezone')
            else:
                if isinstance(date, datetime.datetime):
                    date = pytz.timezone(value).localize(date)
        else:
            errors[tz_key].append(_('Timezone is required.'))
        return date

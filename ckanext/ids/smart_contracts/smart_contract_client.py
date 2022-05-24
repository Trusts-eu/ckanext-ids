import json
import os
import requests


URL_SUBDIRECTORIES = {
    'basic_create_asset': 'basic/createasset',
    'basic_get_all_assets': 'basic/getallassets',
    'basic_init_ledger': 'basic/initledger',
    'basic_transfer_asset': 'basic/transferasset',
    'basic_update_asset': 'basic/updateasset',
    'scoring_get_all_scores': 'scoring/getallscores',
    'scoring_init_ledger': 'scoring/initledger',
    'scoring_update': 'scoring/updatescore',
    'secure_agree_to_buy': 'secure/agreetobuy',
    'secure_agree_to_sell': 'secure/agreetosell',
    'secure_create_asset': 'secure/createasset',
    'secure_read_asset': 'secure/readasset',
    'secure_read_bid_price': 'secure/readbidprice',
    'secure_read_sale_price': 'secure/readsaleprice',
    'secure_transfer_asset': 'secure/transferasset',
    'secure_update_description': 'secure/updatedescription',
    'secure_verify_asset': 'secure/verifyasset',
    }


def make_request_to_smart_contract_api(base_url):

    headers = {'Content-Type': 'application/json'}

    def __create_urls(base_url):
        return {method_name: os.path.join(base_url, url_subdirectory)
                for method_name, url_subdirectory
                in URL_SUBDIRECTORIES.items()}

    urls = __create_urls(base_url)

    def send_request_to_smart_contract_api(kind, data):
        return requests.get(urls[kind],
                            headers=headers,
                            data=json.dumps(data))

    return send_request_to_smart_contract_api

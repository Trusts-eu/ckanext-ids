from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.metadatabroker.client import graphs_to_ckan_result_format

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import logging
from typing import Set, List, Dict
from ckan.common import config
import requests

import urllib.parse

#logger
log = logging.getLogger("ckanext")

#recomm service setup
recomm_di_host="http://recomm-di"
recomm_sp_host="http://recomm-sp" #config.get("ckanext.ids.trusts_local_dataspace_connector_url")

ckan_url= config.get("ckan.site_url") #config.get("ckanext.ids.trusts_local_dataspace_connector_port")

data_ingestion_port="9090"
service_provider_port="9092"

service_provider_path=recomm_sp_host + ":" + service_provider_port

process_external_url = ckan_url + "/ids/processExternal?uri="

store_interaction_path="/trusts/interaction/store"

interaction_ingestion_url=recomm_di_host + ":" + data_ingestion_port + store_interaction_path

recomm_application_to_user_path="/trusts/reco/ruc2/application-user"
recomm_dataset_to_user_path="/trusts/reco/ruc1/dataset-user"
recomm_service_to_user_path="/trusts/reco/ruc2/service-user"

recomm_application_to_application_path="/trusts/reco/ruc6/application-application"
recomm_application_to_dataset_path="/trusts/reco/ruc4/application-dataset"
recomm_application_to_service_path="/trusts/reco/ruc6/application-service"

recomm_dataset_to_application_path="/trusts/reco/ruc3/dataset-application"
recomm_dataset_to_dataset_path="/trusts/reco/ruc5/dataset-dataset"
recomm_dataset_to_service_path="/trusts/reco/ruc3/dataset-service"

recomm_service_to_application_path="/trusts/reco/ruc6/service-application"
recomm_service_to_dataset_path="/trusts/reco/ruc4/service-dataset"
recomm_service_to_service_path="/trusts/reco/ruc6/service-service"

recomm_dataset_to_user_url=service_provider_path + recomm_dataset_to_user_path
recomm_service_to_user_url=service_provider_path + recomm_service_to_user_path
recomm_application_to_user_url=service_provider_path + recomm_application_to_user_path

recomm_application_to_application_url=service_provider_path + recomm_application_to_application_path
recomm_application_to_dataset_url=service_provider_path + recomm_application_to_dataset_path
recomm_application_to_service_url=service_provider_path + recomm_application_to_service_path

recomm_dataset_to_application_url=service_provider_path + recomm_dataset_to_application_path
recomm_dataset_to_dataset_url=service_provider_path + recomm_dataset_to_dataset_path
recomm_dataset_to_service_url=service_provider_path + recomm_dataset_to_service_path

recomm_service_to_application_url=service_provider_path + recomm_service_to_application_path
recomm_service_to_dataset_url=service_provider_path + recomm_service_to_dataset_path
recomm_service_to_service_url=service_provider_path + recomm_service_to_service_path

#request headers
headers={"Content-type": "application/json", "accept": "application/json;charset=UTF-8"}

#entity types
type_application="application"
type_dataset="dataset"
type_service="service"

#interaction types
download_interaction_type="download"
view_recomm_interaction_type="view_recomm"
publish_interaction_type="publish"
accept_contract_interaction_type="accept_contract"
view_interaction_type="view"

def recomm_recomm_applications_sidebar(
    entity, 
    count):
    
    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = get_recomm_sidebar_params(
            userId,
            entity, 
            count)
            
        url = get_recomm_applications_sidebar_url(
            entity['type'])
            
        if 'userId' not in params:
            recomm_log("Failed to recommended applications for " + entity['type'] + ": " + entity['id'])
            return []
        
        response = requests.get(
            url=url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended applications for " + entity['type'] + ": " + entity['id'])

            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended applications for " + entity['type'] + ": " + entity['id'])
            return []
        
    except Exception as error:
        recomm_log("Failed to recommended applications")
        return []    

def recomm_recomm_datasets_sidebar(
    entity, 
    count):
    
    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = get_recomm_sidebar_params(
            userId, 
            entity, 
            count)
            
        url = get_recomm_datasets_sidebar_url(
            entity['type'])
            
        if 'userId' not in params:
            recomm_log("Failed to recommended datasets for " + entity['type'] + ": " + entity['id'])
            return []
        
        response = requests.get(
            url=url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended datasets for " + entity['type'] + ": " + entity['id'])
            
            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended datasets for " + entity['type'] + ": " + entity['id'])
            return []
            
    except Exception as error:
        recomm_log("Failed to recommended datasets")
        return []        
        
def recomm_recomm_services_sidebar(
    entity, 
    count):
    
    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = get_recomm_sidebar_params(
            userId, 
            entity, 
            count)
            
        url = get_recomm_services_sidebar_url(
            entity['type'])
        
        if 'userId' not in params:
            recomm_log("Failed to recommended services for " + entity['type'] + ": " + entity['id'])
            return []
        
        response = requests.get(
            url=url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended services for " + entity['type'] + ": " + entity['id'])
            
            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended services for " + entity['type'] + ": " + entity['id'])
            return []
            
    except Exception as error:
        recomm_log("Failed to recommended services")
        return []        

def recomm_recomm_datasets_homepage(
    count):
    
    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = {
            "userId": userId, 
            "count": count
        }
        
        response = requests.get(
            url=recomm_dataset_to_user_url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended datasets for user: " + userId)
            
            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended datasets for user: " + userId)
            return []
    
    except Exception as error:
        recomm_log("Failed to recommended datasets for user")
        return []           

def recomm_recomm_services_homepage(
    count):

    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = {
            "userId": userId, 
            "count": count
        }
        
        response = requests.get(
            url=recomm_service_to_user_url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended services for user: " + userId)
            
            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended services for user: " + userId)
            return []
            
    except Exception as error:
        recomm_log("Failed to recommended services for user")
        return []       
    
def recomm_recomm_applications_homepage(
    count):
    
    try:
        userId = plugins.toolkit.g.userobj.id
        
        params = {
            "userId": userId, 
            "count": count
        }
        
        response = requests.get(
            url=recomm_application_to_user_url, 
            params=params,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully recommended applications for user: " + userId)
            
            return format_results(response)

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to recommended applications for user: " + userId)
            return []
    
    except Exception as error:
        recomm_log("Failed to recommended applications for user")
        return []    

def recomm_store_download_interaction(
    entityId: str):
    
    try:
        entity = recomm_retrieve_entity(entityId)
        
        if entity is None:
            return False

        data = {
            "entityId": entity["id"],
            "entityType": entity["type"],
            "type": download_interaction_type, 
            "userId": plugins.toolkit.g.userobj.id
        }
    
        response = requests.post(
            url=interaction_ingestion_url,
            json=data,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully stored download interaction for: " + entityId)
            return True

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to store download interaction for: " + entityId)
            return False

    except Exception as error:
        recomm_log("Failed to store download interaction")
        return False
        
def recomm_store_view_recomm_interaction(
    entityId: str, 
    recoId: str):
    
    try:
        entity = recomm_retrieve_entity(entityId)
        
        if entity is None:
            return False

        data = {
            "entityId": entity["id"],
            "entityType": entity["type"],
            "type": view_recomm_interaction_type, 
            "userId": plugins.toolkit.g.userobj.id, 
            "recommenderId": recoId
        }
   
        response = requests.post(
            url=interaction_ingestion_url,
            json=data,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully stored view recomm interaction for: " + entityId)
            return True

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to store view recomm interaction for: " + entityId)
            return False
            
    except Exception as error:
        recomm_log("Failed to store view recomm interaction")
        return False            

def recomm_store_publish_interaction(
    entityId: str, 
    entityType: str):
    
    try:
        data = {
            "entityId": entityId,
            "entityType": entityType,
            "type": publish_interaction_type, 
            "userId": plugins.toolkit.g.userobj.id
        }
        
        response = requests.post(
            url=interaction_ingestion_url,
            json=data,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully stored publish interaction for: " + entityId)
            return True

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to store publish interaction for: " + entityId)
            return False
            
    except Exception as error:
        recomm_log("Failed to store publish interaction")
        return False    

def recomm_store_accept_contract_interaction(
    entityId: str):
    
    try:
        entity = recomm_retrieve_entity(entityId)
        
        if entity is None:
            return False
            
        data = {
            "entityId": entity["id"],
            "entityType": entity["type"],
            "type": accept_contract_interaction_type, 
            "userId": plugins.toolkit.g.userobj.id
        }
        
        response = requests.post(
            url=interaction_ingestion_url,
            json=data,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully stored accept contract interaction for: " + entityId)
            return True

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to store accept contract interaction for: " + entityId)
            return False
            
    except Exception as error:
        recomm_log("Failed to store accept contract interaction")
        return False    
        
def recomm_store_view_interaction(
    entityId: str, 
    entityType: str):
    
    try:
        data = {
            "entityId": entityId, 
            "entityType": entityType,
            "type": view_interaction_type, 
            "userId": plugins.toolkit.g.userobj.id
        }
    
        response = requests.post(
            url=interaction_ingestion_url,
            json=data,
            headers=headers)

        if response.status_code == 200:
            recomm_log("Sucessfully stored view interaction for: " + entityId)
            return True

        if response.status_code > 200 or response.text is None:
            recomm_log("Failed to store view interaction for: " + entityId)
            return False
            
    except Exception as error:
        recomm_log("Failed to store view interaction")
        return False            
        
def recomm_retrieve_entity(
    entityId: str):
    
    local_connector = Connector()
    
    try:
        entityGraphs = local_connector.ask_broker_for_description(element_uri=entityId)
        entity = graphs_to_ckan_result_format(entityGraphs)
    
        return entity

    except Exception as error:
        recomm_log("Failed to retrieve entity: " + entityId)
        return None    

#def recomm_get_interaction_type(
#    entityType: str,
#    interactionType: str):
#    
#    if entityType == type_dataset:
#        interactionType += "_" + type_dataset
#    if entityType == type_service:
#        interactionType += "_" + type_service
#    if entityType == type_application:
#        interactionType += "_" + type_application
#    
#    return interactionType
    
def recomm_log(
    logMessage: str):
    
    log.info("-------------------------");
    log.info("-------------------------");
    log.info("RECOMM | " + logMessage);
    log.info("-------------------------");
    log.info("-------------------------");
    
    return True

def get_recomm_sidebar_params(
    userId:str,
    entity, 
    count):
    
    if(entity['type'] == type_application):
        return {
            "userId": userId, 
            "applicationId": entity['id'],
            "count": count
        }
        
    if(entity['type'] == type_dataset):
        return {
            "userId": userId, 
            "datasetId": entity['id'],
            "count": count
        }
        
    if(entity['type'] == type_service):
        return {
            "userId": userId, 
            "serviceId": entity['id'],
            "count": count
        }  
            
    return {}
    
def get_recomm_applications_sidebar_url(
    entityType:str):
    
    if(entityType == type_application):
        return recomm_application_to_application_url
        
    if(entityType == type_dataset):
        return recomm_application_to_dataset_url
        
    if(entityType == type_service):
        return recomm_application_to_service_url

    return ""

def get_recomm_datasets_sidebar_url(
    entityType:str):
    
    if(entityType == type_application):
        return recomm_dataset_to_application_url
        
    if(entityType == type_dataset):
        return recomm_dataset_to_dataset_url
        
    if(entityType == type_service):
        return recomm_dataset_to_service_url

    return ""

def get_recomm_services_sidebar_url(
    entityType:str):
    
    if(entityType == type_application):
        return recomm_service_to_application_url
        
    if(entityType == type_dataset):
        return recomm_service_to_dataset_url
        
    if(entityType == type_service):
        return recomm_service_to_service_url

    return ""

def format_results(response):

    jsonResponse = response.json()
    entities = []
        
    for result in reversed(jsonResponse["results"]):
        
        result['pkg_id'] = result['id']
        result['id'] = process_external_url + urllib.parse.quote_plus(result['id'])
        result['recoId'] = jsonResponse["reco_id"]
        
        entities.append(result)

    return entities
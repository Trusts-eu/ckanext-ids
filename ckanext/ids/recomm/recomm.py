from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.metadatabroker.client import graphs_to_ckan_result_format

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import logging
from typing import Set, List, Dict
from ckan.common import config
import requests

#logger
log = logging.getLogger("ckanext")

#recomm service setup
host=config.get("ckanext.ids.trusts_local_dataspace_connector_url")
data_ingestion_port="9090"
service_provider_port="9092"
store_interaction_path="/trusts/interaction/store"
recomm_dataset_to_user_path="/trusts/reco/ruc1/dataset-user"
recomm_service_to_user_path="/trusts/reco/ruc2/service-user"
recomm_application_to_user_path="/trusts/reco/ruc2/application-user"
interaction_ingestion_url=host + ":" + data_ingestion_port + store_interaction_path
recomm_dataset_to_user_url=host + ":" + service_provider_port + recomm_dataset_to_user_path
recomm_service_to_user_url=host + ":" + service_provider_port + recomm_service_to_user_path
recomm_application_to_user_url=host + ":" + service_provider_port + recomm_application_to_user_path

#request headers
headers={"Content-type": "application/json", "accept": "application/json;charset=UTF-8"}

#entity types
type_dataset="dataset"
type_service="service"
type_application="application"

#interaction types
download_interaction_type="download"
publish_interaction_type="publish"
accept_contract_interaction_type="accept_contract"
view_interaction_type="view"

def recomm_recomm_datasets_homepage():
    
    userId = plugins.toolkit.g.userobj.id
    
    params = {
        "userId": userId, 
        "count": "3",
        "algo": "MP"
    }
    
    response = requests.get(
        url=recomm_dataset_to_user_url, 
        params=params,
        headers=headers)

    if response.status_code == 200:
        recomm_log("Sucessfully recommended datasets for user: " + userId)
        
        datasetTitles = []
        
        for result in response.json()["results"]:
            datasetTitles.append(result["title"])
            
        return datasetTitles

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to recommended datasets for user: " + userId);
        return []

def recomm_recomm_services_homepage():

    userId = plugins.toolkit.g.userobj.id
    
    params = {
        "userId": userId, 
        "count": "3",
        "algo": "MP"
    }
    
    response = requests.get(
        url=recomm_service_to_user_url, 
        params=params,
        headers=headers)

    if response.status_code == 200:
        recomm_log("Sucessfully recommended services for user: " + userId)
        
        serviceTitles = []
        
        for result in response.json()["results"]:
            serviceTitles.append(result["title"])
            
        return serviceTitles

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to recommended services for user: " + userId);
        return []
    
def recomm_recomm_applications_homepage():
    
    userId = plugins.toolkit.g.userobj.id
    
    params = {
        "userId": userId, 
        "count": "3",
        "algo": "MP"
    }
    
    response = requests.get(
        url=recomm_application_to_user_url, 
        params=params,
        headers=headers)

    if response.status_code == 200:
        recomm_log("Sucessfully recommended applications for user: " + userId)
        
        applicationTitles = []
        
        for result in response.json()["results"]:
            applicationTitles.append(result["title"])
            
        return applicationTitles

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to recommended applications for user: " + userId);
        return []

def recomm_store_download_interaction(
    entityId: str):
    
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
        recomm_log("Sucessfully stored download interaction for: " + entityId);
        return True

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to store download interaction for: " + entityId);
        return False

def recomm_store_publish_interaction(
    entityId: str, 
    entityType: str):
    
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
        recomm_log("Sucessfully stored publish interaction for: " + entityId);
        return True

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to store publish interaction for: " + entityId);
        return False

def recomm_store_accept_contract_interaction(
    entityId: str):
    
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
        recomm_log("Sucessfully stored accept contract interaction for: " + entityId);
        return True

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to store accept contract interaction for: " + entityId);
        return False
        
def recomm_store_view_interaction(
    entityId: str, 
    entityType: str):
    
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
        recomm_log("Sucessfully stored view interaction for: " + entityId);
        return True

    if response.status_code > 200 or response.text is None:
        recomm_log("Failed to store view interaction for: " + entityId);
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
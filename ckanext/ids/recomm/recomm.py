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
data_ingestion_host=config.get("ckanext.ids.trusts_local_dataspace_connector_url")
data_ingestion_port="9090"
store_interaction_path="/trusts/interaction/store"
interaction_ingestion_url=data_ingestion_host + ":" + data_ingestion_port + store_interaction_path

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

def recomm_store_download_interaction(
    entityId: str):
    
    entity = recomm_retrieve_entity(entityId)
    
    if entity is None:
        return False
    
    interactionType = recomm_get_interaction_type(
        entity["type"],
        download_interaction_type)
    
    if interactionType == download_interaction_type:
        return False
    
    data = {
        "entityId": entity["id"],
        "type": interactionType, 
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
    
    interactionType = recomm_get_interaction_type(
        entityType,
        publish_interaction_type)
    
    if interactionType == publish_interaction_type:
        return False
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
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
        
    interactionType = recomm_get_interaction_type(
        entity["type"],
        accept_contract_interaction_type)
    
    if interactionType == accept_contract_interaction_type:
        return False
    
    data = {
        "entityId": entity["id"], 
        "type": interactionType, 
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
    
    interactionType = recomm_get_interaction_type(
        entityType,
        view_interaction_type)
    
    if interactionType == view_interaction_type:
        return False
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
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

def recomm_get_interaction_type(
    entityType: str,
    interactionType: str):
    
    if entityType == type_dataset:
        interactionType += "_" + type_dataset
    if entityType == type_service:
        interactionType += "_" + type_service
    if entityType == type_application:
        interactionType += "_" + type_application
    
    return interactionType
    
def recomm_log(
    logMessage: str):
    
    log.info("-------------------------");
    log.info("-------------------------");
    log.info("RECOMM | " + logMessage);
    log.info("-------------------------");
    log.info("-------------------------");
    
    return True
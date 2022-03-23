import logging
from typing import Set, List, Dict
from ckan.common import config
import requests

log = logging.getLogger("ckanext")
data_ingestion_host=config.get("ckanext.ids.trusts_local_dataspace_connector_url")
data_ingestion_port="9090"
store_interaction_path="/trusts/interaction/store"
interaction_ingestion_url=data_ingestion_host + ":" + data_ingestion_port + store_interaction_path
headers={"Content-type": "application/json", "accept": "application/json;charset=UTF-8"}

def recomm_store_download_interaction(
    userId: str,
    entityId: str, 
    entityType: str):
    
    interactionType = None
    
    if entityType == "dataset":
        interactionType = "download_dataset"
    if entityType == "service":
        interactionType = "download_service"
    if entityType == "application":
        interactionType = "download_application"
    
    if interactionType is None:
        return
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
        "userId": userId
    }
    
    response = requests.post(
        url=interaction_ingestion_url,
        json=data,
        headers=headers)

    if response.status_code == 200:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Sucessfully stored download interaction")
        #log.info(str(data))
        #log.info(str(entity));
        log.info("-------------------------");
        log.info("-------------------------");
        return True

    if response.status_code > 200 or response.text is None:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Failed to store download interaction")
        #log.error(str(response.text))
        #log.error(str(data))
        log.info("-------------------------");
        log.info("-------------------------");   
        return False
        
def recomm_store_publish_interaction(
    userId: str,
    entityId: str, 
    entityType: str):
    
    interactionType = None
    
    if entityType == "dataset":
        interactionType = "publish_dataset"
    if entityType == "service":
        interactionType = "publish_service"
    if entityType == "application":
        interactionType = "publish_application"
    
    if interactionType is None:
        return
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
        "userId": userId
    }
    
    response = requests.post(
        url=interaction_ingestion_url,
        json=data,
        headers=headers)

    if response.status_code == 200:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Sucessfully stored publish interaction")
        #log.info(str(data))
        #log.info(str(entity));
        log.info("-------------------------");
        log.info("-------------------------");
        return True

    if response.status_code > 200 or response.text is None:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Failed to store publish interaction")
        #log.error(str(response.text))
        #log.error(str(data))
        log.info("-------------------------");
        log.info("-------------------------");   
        return False

def recomm_store_accept_contract_interaction(
    userId: str,
    entityId: str, 
    entityType: str):
    
    interactionType = None
    
    if entityType == "dataset":
        interactionType = "accept_contract_dataset"
    if entityType == "service":
        interactionType = "accept_contract_service"
    if entityType == "application":
        interactionType = "accept_contract_application"
    
    if interactionType is None:
        return
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
        "userId": userId
    }
    
    response = requests.post(
        url=interaction_ingestion_url,
        json=data,
        headers=headers)

    if response.status_code == 200:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Sucessfully stored accept contract interaction")
        #log.info(str(data))
        #log.info(str(entity));
        log.info("-------------------------");
        log.info("-------------------------");
        return True

    if response.status_code > 200 or response.text is None:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Failed to store accept contract interaction")
        #log.error(str(response.text))
        #log.error(str(data))
        log.info("-------------------------");
        log.info("-------------------------");   
        return False
        
def recomm_store_view_interaction(
    userId: str,
    entityId: str, 
    entityType: str):
    
    interactionType = None
    
    if entityType == "dataset":
        interactionType = "view_dataset"
    if entityType == "service":
        interactionType = "view_service"
    if entityType == "application":
        interactionType = "view_application"
    
    if interactionType is None:
        return
    
    data = {
        "entityId": entityId, 
        "type": interactionType, 
        "userId": userId
    }
    
    response = requests.post(
        url=interaction_ingestion_url,
        json=data,
        headers=headers)

    if response.status_code == 200:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Sucessfully stored view interaction")
        #log.info(str(data))
        #log.info(str(entity));
        log.info("-------------------------");
        log.info("-------------------------");
        return True

    if response.status_code > 200 or response.text is None:
        log.info("-------------------------");
        log.info("-------------------------");
        log.info("RECOMM | Failed to store view interaction")
        #log.error(str(response.text))
        #log.error(str(data))
        log.info("-------------------------");
        log.info("-------------------------");   
        return False
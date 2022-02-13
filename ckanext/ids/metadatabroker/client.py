import hashlib
import logging

import logging
import urllib.parse

from typing import Set, List, Dict

import cachetools.func
import ckan.lib.dictization
import ckan.logic as logic
import rdflib
from ckan.common import config

from urllib.parse import urlparse

from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.metadatabroker.translations_broker_ckan import URI, \
    empty_result

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_table_dictize = ckan.lib.dictization.table_dictize
_check_access = logic.check_access
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

# log = logging.getLogger('ckan.logic')
log = logging.getLogger("ckanext")

connector = Connector()
log.info("Using " + connector.broker_url + " as broker URL")

idsresource = rdflib.URIRef("https://w3id.org/idsa/core/Resource")

rdftype = rdflib.namespace.RDF["type"]


def _grouping_from_table_to_dict(triples_list: List[Dict],
                                 grouping_column: str = "s",
                                 key_column: str = "p",
                                 value_clumn: str = "o"):
    allgroups = set([x[grouping_column] for x in triples_list])
    allkeys = set([x[key_column] for x in triples_list])
    result = {x: {k: [] for k in allkeys}
              for x in allgroups}
    for t in triples_list:
        g = t[grouping_column]
        k = t[key_column]
        v = t[value_clumn]

        result[g][k].append(v)

    return result


def _parse_broker_tabular_response(raw_text, sep="\t"):
    readrows = 0
    result = []
    for irow, row in enumerate(raw_text.split("\n")):
        rows = row.strip()
        if len(rows) < 1:
            continue
        vals = rows.split(sep)
        if irow == 0:
            colnames = [x.replace("?", "") for x in vals]
            continue
        d = {cname: vals[ci]
             for ci, cname in enumerate(colnames)}
        result.append(d)

    return result


def _sparql_describe_many_resources(resources: Set[rdflib.URIRef]) -> str:
    query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
               SELECT ?s ?p ?o 
               WHERE { \n"""
    qparts = []
    for res in resources:
        qp = "{ ?s2 ?p ?o . \n"
        qp += "  ?s2 owl:sameAs " + res.n3() + " .\n"
        qp += "  BIND (URI(" + res.n3() + ") as ?s ) .}"
        qp += "UNION { " + res.n3() + " ?p ?o. "
        qp += "         BIND (URI(" + res.n3() + ") as ?s ) .}"
        qparts.append(qp)
    query += "\nUNION\n".join(qparts)
    query += "}"

    return query


# ToDo uncomment filter statement
def _sparl_get_all_resources(resource_type: str,
                             type_pred="https://www.trusts-data.eu/ontology/asset_type"):
    catalogiri = URI(config.get("ckanext.ids.connector_catalog_iri")).n3()

    query = """
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      SELECT ?resultUri ?type  WHERE
      { ?resultUri a ?type . 
        ?conn <https://w3id.org/idsa/core/offeredResource> ?resultUri .
        #FILTER NOT EXISTS { ?conn owl:sameAs """ + catalogiri + """ }
    
        """
    if resource_type is None or resource_type == "None":
        pass
    else:
        typeuri = URI("https://www.trusts-data.eu/ontology/" + \
                      resource_type.capitalize())
        query += "\n ?resultUri " + URI(type_pred).n3() + typeuri.n3() + "."
    query += "\n}"
    return query


def listofdicts2graph(lod: List[Dict],
                      s: str = "s",
                      p: str = "p",
                      o: str = "o"):
    g = rdflib.Graph()
    for ri in lod:
        s = URI(ri[s])
        p = URI(ri[p])
        if ri[o].startswith("<") and ri[o].endswith(">"):
            o = URI(ri[o])
        else:
            o = rdflib.Literal(ri[o])
        g.add((s, p, o))

    return g

def _to_ckan_package(raw_jsonld: Dict):
    package = dict()
    package['title'] = raw_jsonld['ids:title'][0]['@value']
    package['name'] = hashlib.sha256(raw_jsonld['@id'].encode('utf-8')).hexdigest()
    package['description'] = raw_jsonld['ids:description'][0]['@value']
    package['version'] = raw_jsonld['ids:version']
    package['theme'] = raw_jsonld['https://www.trusts-data.eu/ontology/theme']['@id']
    package['type'] = get_resource_type(raw_jsonld['https://www.trusts-data.eu/ontology/asset_type']['@id'])
    package['owner_org'] = raw_jsonld['ids:publisher']['@id']
    return package

def get_resource_type(type):
    if type == "https://www.trusts-data.eu/ontology/Dataset":
        return "dataset"
    elif type == "https://www.trusts-data.eu/ontology/Application":
        return "appplication"
    elif type == "https://www.trusts-data.eu/ontology/Service":
        return "service"
    else:
        raise ValueError("Uknown dataset type: " + type + " Mapping failed.")


def graphs_to_contracts(raw_jsonld: Dict):
    g = raw_jsonld["@graph"]
    contract_graphs = [x for x in g if x["@type"] == "ids:ContractOffer"]
    resource_graphs = [x for x in g if x["@type"] == "ids:Resource"]
    permission_graphs = [x for x in g if x["@type"] == "ids:Permission"]
    artifact_graphs = [x for x in g if x["@type"] == "ids:Artifact"]

    resource_uri = resource_graphs[0]["sameAs"]
    theirname = resource_uri
    organization_name = theirname.split("/")[2].split(":")[0]
    # FIXME: Is this correct ?
    providing_base_url = "/".join(organization_name.split("/")[:3])

    permission_graph_dict = {x["@id"]:x for x in permission_graphs}
    results = []
    for cg in contract_graphs:
        perm_graph = permission_graph_dict[cg["permission"]]
        r = dict()
        r["contract_start"] = cg["contractStart"]
        r["contract_end"] = cg["contractEnd"]
        r["title"] = resource_graphs[0]["title"]
        r["errors"] = {}
        r["policies"] = [{"type": perm_graph["description"].upper().replace("-","_")}]
        r["provider_url"] = providing_base_url
        ## FIXME: hack to replace the urls, now hardocoded, perhaps we should a property in resource??? This will also fix the issue with provider_url
        r["resourceId"] = rewrite_urls("provider-core:8080", resource_uri)
        r["artifactId"] = rewrite_urls("provider-core:8080", artifact_graphs[0]["sameAs"])
        r["contractId"] = rewrite_urls("provider-core:8080", cg["sameAs"])
        results.append(r)

    return results

def rewrite_urls(provider_base, input_url):
    a = urlparse(input_url)
    return a._replace(netloc=provider_base).geturl()


def graphs_to_ckan_result_format(raw_jsonld: Dict):
    g = raw_jsonld["@graph"]
    resource_graphs = [x for x in g if x["@type"] == "ids:Resource"]
    if "theme" not in resource_graphs[0].keys():
        return None
    representation_graphs = [x for x in g if
                             x["@type"] == "ids:Representation"]
    artifact_graphs = [x for x in g if x["@type"] == "ids:Artifact"]

    resource_uri = resource_graphs[0]["sameAs"]

    # ToDo get this from the central core as well
    theirname = resource_uri
    organization_name = theirname.split("/")[2].split(":")[0]
    providing_base_url = "/".join(organization_name.split("/")[:3])
    organization_data = {
        "id": "52bc9332-2ba1-4c4f-bf85-5a141cd68423",
        "name": organization_name,
        "title": "Orga1",
        "type": "organization",
        "description": "",
        "image_url": "",
        "created": "2022-02-02T16:32:58.653424",
        "is_organization": True,
        "approval_status": "approved",
        "state": "active"
    }
    resources = []

    packagemeta = empty_result
    packagemeta["id"] = resource_uri
    packagemeta["license_id"] = resource_graphs[0]["standardLicense"]
    packagemeta["license_url"] = resource_graphs[0]["standardLicense"]
    packagemeta["license_title"] = resource_graphs[0]["standardLicense"]
    packagemeta["metadata_created"] = resource_graphs[0]["created"]
    packagemeta["metadata_modified"] = resource_graphs[0]["modified"]
    packagemeta["name"] = resource_graphs[0]["title"]
    packagemeta["title"] = resource_graphs[0]["title"]
    packagemeta["type"] = resource_graphs[0]["asset_type"].split("/")[
        -1].lower()
    packagemeta["theme"] = resource_graphs[0]["theme"].split("/")[-1]
    packagemeta["version"] = resource_graphs[0]["version"]

    # These are the values we will use in succesive steps
    packagemeta["external_provider_name"] = organization_name
    packagemeta["to_process_external"] = config.get(
        "ckan.site_url") + "/ids/processExternal?uri=" + \
                                         urllib.parse.quote_plus(
        resource_uri)
    packagemeta["provider_base_url"] = providing_base_url

    packagemeta["creator_user_id"] = "X"
    packagemeta["isopen"]: None
    packagemeta["maintainer"] = None
    packagemeta["maintainer_email"] = None
    packagemeta["notes"] = None
    packagemeta["num_tags"] = 0
    packagemeta["private"] = False
    packagemeta["state"] = "active"
    packagemeta["relationships_as_object"] = []
    packagemeta["relationships_as_subject"] = []
    packagemeta["url"] = "http://my.url"
    packagemeta["tags"] = []  # (/)
    packagemeta["groups"] = []  # (/)

    packagemeta["dataset_count"] = 0
    packagemeta["service_count"] = 0
    packagemeta["application_count"] = 0
    packagemeta[packagemeta["type"] + "count"] = 1

    for rg in representation_graphs:
        empty_ckan_resource = {
            "artifact": rg["instance"],
            "cache_last_updated": None,
            "cache_url": None,
            "created": resource_graphs[0]["created"],
            "description": resource_graphs[0]["description"],
            "format": "__MISSING__",
            "hash": artifact_graphs[0]["checkSum"],
            "id": rg["@id"],
            "last_modified": resource_graphs[0]["modified"],
            "metadata_modified": rg["modified"],
            "mimetype": rg["mediaType"],
            "mimetype_inner": None,
            "name": resource_graphs[0]["title"],
            "package_id": resource_graphs[0]["sameAs"],
            "position": 0,
            "representation": rg["sameAs"],
            "resource_type": "resource",
            "size": artifact_graphs[0]["ids:byteSize"],
            "state": "active",
            "url": rg["sameAs"],
            "url_type": "upload"
        }
        resources.append(empty_ckan_resource)

    packagemeta["organization"] = organization_data
    packagemeta["owner_org"] = organization_data["id"]
    packagemeta["resources"] = resources
    packagemeta["num_resources"] = len(artifact_graphs)

    return packagemeta


@ckan.logic.side_effect_free
@cachetools.func.ttl_cache(3)  # CKan does a bunch equivalent requests in
# rapid succession
def broker_package_search(q=None, start_offset=0, fq=None):
    # log.debug("\n--- STARTING  BROKER SEARCH  ----------------------------\n")
    # log.debug(str(q))
    # log.debug(str(fq))
    # log.debug("-----------------------------------------------------------\n")
    default_search = "*:*"
    search_string = q if q is not None else default_search

    # By default we will search for all sorts of stuff
    requested_type = None
    try:
        if fq is not None:
            requested_type = [x for x in fq
                              if x.startswith("+type")][0]
            requested_type = [x for x in requested_type.split(" ")
                              if x.startswith("+type")]
            requested_type = requested_type[0].split(":")[-1].capitalize()
    except:
        pass

    log.debug("Requested search type was " + str(requested_type) + "\n\n")
    search_results = []
    resource_uris = []

    if len(search_string) > 0 and search_string != default_search:
        raw_response = connector.search_broker(search_string=search_string,
                                               offset=start_offset)
    else:
        log.debug("Default search activated----")
        general_query = _sparl_get_all_resources(resource_type=requested_type)
        raw_response = connector.query_broker(general_query)

    parsed_response = _parse_broker_tabular_response(raw_response)
    resource_uris = set([URI(x["resultUri"])
                         for x in parsed_response
                         if URI(x["type"]) == idsresource])

    if len(resource_uris) > 0:
        log.debug("RESOURCES FOUND <------------------------------------\n")
        for ru in resource_uris:
            log.debug(ru.n3() + " <------------------------------------")
        log.debug("---------------------------||||||||||||||")

    if len(resource_uris) == 0:
        return search_results

    descriptions = {ru.n3(): connector.ask_broker_for_description(ru.n3()[1:-1])
                    for ru in resource_uris}

    log.debug(
        ".\n....................................................................")
    for k, v in descriptions.items():
        log.debug(k)
        pm = graphs_to_ckan_result_format(v)
        log.debug(pm)
        log.debug(
            "------------------------------------------------------------------")
        if pm is not None:
            search_results.append(pm)

    log.debug(
        "\n....................................................................\n\n\n")

    # --------- This was an attempt to do it over SPARQL describe
    # ---------- Should be faster.. but harder to parse
    # log.info("URIs:\n"+"\n".join([x.n3() for x in resource_uris]))
    # query_for_info = _sparql_describe_many_resources(resource_uris)
    # raw_response = connector.query_broker(query_for_info)
    # all_triples = _parse_broker_tabular_response(raw_response)
    # g = listofdicts2graph(all_triples)
    # log.debug("-----INFO FROM BROKER ------------------------------")
    # rj = json.dumps(all_triples, indent=2)
    # for ru in resource_uris:
    #    r = {}
    # log.debug(rj)

    log.debug("---- END BROKER SEARCH ------------\n-----------\n----\n-----")
    return search_results

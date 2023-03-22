import datetime
import hashlib
import json
import logging
import urllib.parse
from copy import deepcopy
from typing import Set, List, Dict
from urllib.parse import urlparse
import re

import ckan.lib.dictization
import ckan.logic as logic
import ckan.lib.helpers as h
from ckanext.scheming.helpers import scheming_get_schema, scheming_field_by_name
import rdflib
from rdflib.plugins.sparql.results.tsvresults import TSVResultParser
from rdflib.term import Variable
from io import StringIO
from ckan.common import config


from ckanext.ids.dataspaceconnector.connector import Connector, ConnectorException
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


def _parse_broker_tabular_response(raw_text):
    parser = TSVResultParser()
    input = StringIO(raw_text)

    result = parser.parse(source=input)
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
def _sparl_get_all_resources(resource_type: str, fts_query: str, fq: list, facet_fields: list,
                             limit: int, offset: int, type_pred="https://www.trusts-data.eu/ontology/asset_type"):
    catalogiri = URI(config.get("ckanext.ids.connector_catalog_iri")).n3()
    #TODO: make this resource type specific
    dataset_schema = scheming_get_schema("dataset", "dataset", True)
    query = """
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX ids: <https://w3id.org/idsa/core/>
      SELECT ?resultUri ?type ?title ?description ?assettype ?externalname ?license ?creationDate
      WHERE
      { ?resultUri a ?type . 
        ?conn <https://w3id.org/idsa/core/offeredResource> ?resultUri .
        ?resultUri ids:title ?title .
        ?resultUri ids:description ?description .
        ?resultUri owl:sameAs ?externalname .
        ?resultUri ids:standardLicense ?license .
        OPTIONAl {  ?resultUri ids:created ?creationDateTemp . }
        BIND (str(coalesce(?creationDateTemp, "Not Specified")) as ?creationDate)
        FILTER (!regex(str(?externalname),\"""" + config.get(
        'ckanext.ids.local_node_name') + """\",\"i\"))
        """
    facet_filters = build_facet_filters(fq, facet_fields, dataset_schema)
    for facet_filter in facet_filters:
        query += facet_filter

    if resource_type is None or resource_type == "None":
        query += "\n ?resultUri " + URI(type_pred).n3() + " ?assettype."
    else:
        typeuri = URI("https://www.trusts-data.eu/ontology/" + \
                      resource_type.capitalize())
        query += "\n ?resultUri " + URI(
            type_pred).n3() + " ?assettype ."
        query += "\nvalues ?assettype { " + typeuri.n3() + " } "
    if fts_query is not None:
        query += "FILTER regex(concat(?title, \" \",?description, \" \",str(?externalname)), \"" + fts_query + "\", \"i\")"
    query += "\n}"
    query += " LIMIT " + str(limit) + " OFFSET " + str(offset)
    return query


def build_facet_filters(fq: list, facet_fields: list, schema: dict):
    facets = dictionize_facet_query(fq, facet_fields, schema)
    facet_filters = []
    for facet in facets:
        facet_dict = facets[facet]
        facet_filter = "?resultUri <" + facet_dict["property"] + "> ?" + facet + ". values ?" + facet +" { " + " ".join(facet_dict["values"]) + " }"
        facet_filters.append(facet_filter)
    return facet_filters


def dictionize_facet_query(fq: list, facet_fields: list, schema: dict):
    facets = {}
    for facet in fq:
        facet_item = facet.split(":", 1)
        facet_key = facet_item[0]
        if facet_key in facet_fields:
            facet_value = sanitize_facet_value(facet_item[1])
            if facet_key in facets.keys():
                facets[facet_key]["values"].append(facet_value)
            else:
                scheming_field_by_name(schema["dataset_fields"], facet_key)
                facets[facet_key] = {
                    "property" : scheming_field_by_name(schema["dataset_fields"], facet_key)["display_property"],
                    "values" : [facet_value]
                }
    return facets


def sanitize_facet_value(value: str):
    result = value
    if "http" in value:
        result = value.lstrip('"').rstrip('"')
        result = "<" + result + ">"
    elif value.startswith('"'):
        result = value.replace('"', '')

    return result

def _sparl_get_facets(resource_type: str, fts_query: str, fq: str, facet_fields, type_pred="https://www.trusts-data.eu/ontology/asset_type"):
    catalogiri = URI(config.get("ckanext.ids.connector_catalog_iri")).n3()
    #TODO: make this resource type specific
    dataset_schema = scheming_get_schema("dataset", "dataset", True)
    facet_properties = []
    for facet_field in facet_fields:
        schema_field = scheming_field_by_name(dataset_schema["dataset_fields"], facet_field)
        if schema_field is not None:
            property = schema_field["display_property"]
            if "://" in property:
                facet_properties.append(URI(property).n3())
            else:
                facet_properties.append(property)


    query = """
          PREFIX  owl:  <http://www.w3.org/2002/07/owl#>
          PREFIX  ids:  <https://w3id.org/idsa/core/>
          SELECT  (count(?resultUri) as ?facet_count) (str(?facet) as ?facet_string) (str(?facet_value) as ?facet_value_string)
          WHERE
          { graph ?g
            {  
                ?conn     ids:offeredResource   ?resultUri .
                ?resultUri  owl:sameAs            ?externalname .
                FILTER (!regex(str(?externalname),\"""" + config.get('ckanext.ids.local_node_name') + """\",\"i\"))               
                OPTIONAL { ?resultUri ?facet ?facet_value }
                VALUES ?facet { """ + " ".join(facet_properties) + """ } """
    facet_filters = build_facet_filters(fq, facet_fields, dataset_schema)
    for facet_filter in facet_filters:
        query += facet_filter
    if resource_type is None or resource_type == "None":
        query += "\n ?resultUri " + URI(type_pred).n3() + " ?assettype."
    else:
        typeuri = URI("https://www.trusts-data.eu/ontology/" + \
                      resource_type.capitalize())
        query += "\n ?resultUri " + URI(
            type_pred).n3() + " ?assettype ."
        query += "\nvalues ?assettype { " + typeuri.n3() + " } "
    if fts_query is not None:
        query += "FILTER regex(concat(?title, \" \",?description, \" \",str(?externalname)), \"" + fts_query + "\", \"i\")"
    query += """ 
            }
          }
          group by ?facet ?facet_value
          order by ?facet DESC(?facet_count) ?facet_value
        """
    # query += " LIMIT " + str(limit) + " OFFSET " + str(offset)
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
    package['name'] = hashlib.sha256(
        raw_jsonld['@id'].encode('utf-8')).hexdigest()
    package['description'] = raw_jsonld['ids:description'][0]['@value']
    package['version'] = raw_jsonld['ids:version']
    package['theme'] = raw_jsonld['https://www.trusts-data.eu/ontology/theme'][
        '@id']
    package['type'] = get_resource_type(
        raw_jsonld['https://www.trusts-data.eu/ontology/asset_type']['@id'])
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


def graphs_to_artifacts(raw_jsonld: Dict):
    g = raw_jsonld["@graph"]
    artifact_graphs = [x for x in g if x["@type"] == "ids:Artifact"]
    return [x["sameAs"] for x in artifact_graphs]


def graphs_to_contracts(raw_jsonld: Dict,
                        broker_resource_uri: str):
    g = raw_jsonld["@graph"]
    contract_graphs = [x for x in g if x["@type"] == "ids:ContractOffer"]
    resource_graphs = [x for x in g if x["@type"] == "ids:Resource"]
    permission_graphs = [x for x in g if x["@type"] == "ids:Permission"]
    artifact_graphs = [x for x in g if x["@type"] == "ids:Artifact"]

    resource_uri = resource_graphs[0]["sameAs"]
    theirname = resource_uri
    organization_name = theirname.split("/")[2].split(":")[0]
    providing_base_url = "/".join(resource_uri.split("/")[:3])

    permission_graph_dict = {x["@id"]: x for x in permission_graphs}
    results = []
    for cg in contract_graphs:
        perms = cg["permission"]
        if not isinstance(perms, list):
            perms = [perms]
        r = dict()
        r["policies"] = [
            {"type": permission_graph_dict[per]["action"].upper().replace(
                "-", "_")} for per in perms]
        r["contract_start"] = cg["contractStart"]
        r["contract_end"] = cg["contractEnd"]
        r["title"] = clean_multilang(resource_graphs[0]["title"])
        r["errors"] = {}
        r["provider_url"] = providing_base_url
        r["resourceId"] = resource_uri
        r["artifactId"] = artifact_graphs[0]["sameAs"]
        r["artifactIds"] = [x["sameAs"] for x in artifact_graphs]
        r["contractId"] = cg["sameAs"]
        r["brokerResourceUri"] = broker_resource_uri

        results.append(r)

    return results


def rewrite_urls(provider_base, input_url):
    a = urlparse(input_url)
    return a._replace(netloc=provider_base).geturl()


# We pass the results of a query with
#    SELECT ?resultUri ?type ?title ?description ?assettype WHERE
def create_moot_ckan_result(binding):

    license = str(binding[Variable("license")])
    externalName = str(binding[Variable("externalname")])
    title = str(binding[Variable("title")])
    description = str(binding[Variable("description")])
    resultUri = str(binding[Variable("resultUri")])
    creationDate = str(binding[Variable("creationDate")])
    assetType = str(binding[Variable("assettype")])

    theirname = externalName
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

    lictit = ""
    if "http://" or "https://" in license:
        lictit = license.split("/")[-1]

    packagemeta = deepcopy(empty_result)
    packagemeta["id"] = resultUri
    packagemeta["license_id"] = license + "LICENSE"
    packagemeta["license_url"] = license + "LICENSE"
    packagemeta["license_title"] = lictit
    packagemeta["metadata_created"] = creationDate
    packagemeta["metadata_modified"] = datetime.datetime.now().isoformat()
    packagemeta["name"] = title
    packagemeta["title"] = title
    packagemeta["description"] = description + "DESCRIPTION"
    packagemeta["type"] = assetType.split("/")[
        -1].lower()
    packagemeta["theme"] = "THEME"
    packagemeta["version"] = "VERSION"

    # These are the values we will use in succesive steps
    packagemeta["external_provider_name"] = organization_name
    packagemeta["to_process_external"] = config.get(
        "ckan.site_url") + "/ids/processExternal?uri=" + \
                                         urllib.parse.quote_plus(
                                             resultUri)
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
    packagemeta["url"] = providing_base_url
    packagemeta["tags"] = []  # (/)
    packagemeta["groups"] = []  # (/)

    packagemeta["dataset_count"] = 0
    packagemeta["service_count"] = 0
    packagemeta["application_count"] = 0
    packagemeta[packagemeta["type"] + "count"] = 1

    empty_ckan_resource = {
        "artifact": "http://artifact.uri/",
        "cache_last_updated": None,
        "cache_url": None,
        "created": datetime.datetime.now().isoformat(),
        "description": description,
        "format": "EXTERNAL",
        "hash": "SOMEHASH",
        "id": "http://artifact.uri/",
        "last_modified": datetime.datetime.now().isoformat(),
        "metadata_modified": datetime.datetime.now().isoformat(),
        "mimetype": "MEDIATYPE",
        "mimetype_inner": None,
        "name": title,
        "package_id": resultUri,
        "position": 0,
        "representation": "http://artifact.uri/",
        "resource_type": "resource",
        "size": 999,
        "state": "active",
        "url": "http://artifact.uri/",
        "url_type": "upload"
    }
    resources.append(empty_ckan_resource)

    packagemeta["organization"] = organization_data
    packagemeta["owner_org"] = organization_data["id"]
    packagemeta["resources"] = resources
    packagemeta["num_resources"] = 1
    # log.error(json.dumps(packagemeta,indent=1)+"\n.\n.\n.\n\n")

    return packagemeta


def clean_multilang(astring: str):
    if isinstance(astring, str):
        return astring
    if isinstance(astring, dict) and "@value" in astring.keys():
        return str(astring["@value"])
    return str(astring)


def graphs_to_ckan_result_format(raw_jsonld: Dict):
    g = raw_jsonld["@graph"]
    resource_graphs = [x for x in g if x["@type"] == "ids:Resource"]
    if "theme" not in resource_graphs[0].keys():
        return None
    representation_graphs = [x for x in g if
                             x["@type"] == "ids:Representation"]
    artifact_graphs = [x for x in g if x["@type"] == "ids:Artifact"]

    resource_uri = resource_graphs[0]["sameAs"]

    """
    print(10*"\n"+"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~>>")
    print("\nresource_graphs = \n",json.dumps(resource_graphs,
                                            indent=1).replace("\n","\n\t"))
    print("\nartifact_graphs = \n", json.dumps(artifact_graphs,
                                             indent=1).replace("\n", "\n\t"))
    print("\nrepresentation_graphs = \n", json.dumps(representation_graphs,
                                             indent=1).replace("\n", "\n\t"))
    print("\n<<~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"+10 * "\n")
    """

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

    packagemeta = deepcopy(empty_result)
    packagemeta["id"] = resource_uri
    packagemeta["license_id"] = resource_graphs[0][
        "standardLicense"] if "standardLicense" in resource_graphs[0] else None
    packagemeta["license_url"] = resource_graphs[0][
        "standardLicense"] if "standardLicense" in resource_graphs[0] else None
    packagemeta["license_title"] = resource_graphs[0][
        "standardLicense"] if "standardLicense" in resource_graphs[0] else None
    packagemeta["metadata_created"] = resource_graphs[0]["created"]
    packagemeta["metadata_modified"] = resource_graphs[0]["modified"]
    packagemeta["name"] = clean_multilang(resource_graphs[0]["title"])
    packagemeta["title"] = clean_multilang(resource_graphs[0]["title"])
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
    packagemeta["url"] = providing_base_url
    packagemeta["tags"] = []  # (/)
    packagemeta["groups"] = []  # (/)

    packagemeta["dataset_count"] = 0
    packagemeta["service_count"] = 0
    packagemeta["application_count"] = 0
    packagemeta[packagemeta["type"] + "count"] = 1

    for rg in representation_graphs:
        artifact_this_res = [x for x in artifact_graphs
                             if x["@id"] == rg["instance"]][0]
        # logging.error(json.dumps(artifact_this_res,indent=1)+
        #              "\n~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        empty_ckan_resource = {
            "artifact": artifact_this_res["@id"],
            "cache_last_updated": None,
            "cache_url": None,
            "created": resource_graphs[0]["created"],
            "description": clean_multilang(resource_graphs[0]["description"]),
            "format": "EXTERNAL",
            "hash": artifact_this_res["checkSum"],
            "id": rg["@id"],
            "last_modified": resource_graphs[0]["modified"],
            "metadata_modified": rg["modified"],
            "mimetype": rg["mediaType"],
            "mimetype_inner": None,
            "name": artifact_this_res["fileName"],
            "package_id": resource_graphs[0]["sameAs"],
            "position": 0,
            "representation": rg["sameAs"],
            "resource_type": "resource",
            "size": artifact_this_res["ids:byteSize"],
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
def broker_package_search(q=None, start_offset=0, limit=None, fq=None, facet_fields=None):
    log.debug("\n--- STARTING  BROKER SEARCH  ----------------------------\n")
    log.debug(str(q))
    log.debug(str(fq))
    log.debug("-----------------------------------------------------------\n")
    default_search = "*:*"
    search_string = None if q == default_search else q

    # By default we will search for all sorts of stuff
    requested_type = None
    try:
        if fq is not None:
            requested_type = [x for x in fq
                              if "+dataset_type" in x][0]
            requested_type = [x for x in requested_type.split(" ")
                              if x.startswith("+dataset_type")]
            requested_type = requested_type[0].split(":")[-1].capitalize()
    except:
        pass

    # log.debug("Requested search type was " + str(requested_type) + "\n\n")
    search_results = []


    if False:
    #if len(search_string) > 0 and search_string != default_search:
        raw_response = connector.search_broker(search_string=search_string,
                                               offset=start_offset, limit=limit)
        parsed_response = _parse_broker_tabular_response(raw_response)
        resource_uris = set([URI(x["resultUri"])
                             for x in parsed_response
                             if URI(x["type"]) == idsresource])
        descriptions = {
            ru.n3(): connector.ask_broker_for_description(ru.n3()[1:-1])
            for ru in resource_uris}

        for k, v in descriptions.items():
            pm = graphs_to_ckan_result_format(v)
            if pm is not None:
                search_results.append(pm)
    else:
        general_query = _sparl_get_all_resources(resource_type=requested_type, fts_query=search_string,
                                                 fq=fq, facet_fields=facet_fields, limit=limit, offset=start_offset)
        log.debug("Default search activated---- type:" + str(requested_type))
        # log.debug("QUERY :\n\t" + str(general_query).replace("\n", "\n\t"))

        try:
            raw_response = connector.query_broker(general_query)
            parsed_response = _parse_broker_tabular_response(raw_response)
            size_of_broker_results = len(parsed_response.bindings)
        except ConnectorException as e:
            log.debug(e.message)
            h.flash_error("It was not possbile to establish connection to the Broker. Please contact your administrator to investigate further.")
            size_of_broker_results = 0

        if size_of_broker_results > 0:
            log.debug(str(size_of_broker_results) + "   RESOURCES FOUND "
                                                "<------------------------------------\n")

        if size_of_broker_results == 0:
            return search_results

        for res in parsed_response.bindings:
            pm = create_moot_ckan_result(res)
            search_results.append(pm)

        facets_query = _sparl_get_facets(resource_type=requested_type, fts_query=search_string, fq=fq, facet_fields=facet_fields)
        facets_response = connector.query_broker(facets_query)

        parsed_facets_response = _parse_broker_tabular_response(facets_response)
        facets_result = refactor_facets_parsed_response(parsed_facets_response)

    # -- SLOW version
    # descriptions = {
    #     ru.n3(): connector.ask_broker_for_description(ru.n3()[1:-1])
    #     for ru in resource_uris}
    #
    # for k, v in descriptions.items():
    #     pm = graphs_to_ckan_result_format(v)
    #     if pm is not None:
    #         search_results.append(pm)

    # log.debug("---- END BROKER SEARCH ------------\n-----------\n----\n-----")
#    search_results["facets"] = facets
    response = {}
    response["results"] = search_results
    response["facets"] = facets_result
    #TODO: this should come from a different query, now it is just wrong
    response["count"] = len(search_results)
    response["search_facets"] = create_search_facets_object(facets_result)
    return response


def refactor_facets_parsed_response(facets_response):
    facets_result = {}
    dataset_schema = scheming_get_schema("dataset", "dataset", True)
    for facet_response in facets_response.bindings:
        facet_uri = str(facet_response[Variable("facet_string")])
        schema_field = scheming_field_by_display_property(dataset_schema["dataset_fields"], facet_uri)
        if schema_field is not None:
            result = {str(facet_response[Variable("facet_value_string")]):int(str(facet_response[Variable("facet_count")]))}
            field_name = schema_field.get("field_name")
            if field_name in facets_result:
                facets_result[field_name].update(result)
            else:
                facets_result[field_name] = result

    return facets_result


def create_search_facets_object(facets_result:dict):
    search_facets = {}
    for key in facets_result.keys():
        search_facets[key] = {'title': key}
        items = []
        for item_key in facets_result[key].keys():
            items.append({'name':item_key, 'display_name': item_key, 'count': int(facets_result[key][item_key])})
        search_facets[key].update({'items':items})
    return search_facets


def scheming_field_by_display_property(fields, display_property):
    """
    Simple helper to grab a field from a schema field list
    based on the display property passed. Returns None when not found.
    """
    for field in fields:
        try:
            if field.get("display_property") == display_property:
                return field
        except:
            pass


def strip_scheme(url: str):

    if "opendefinition" in url:
        pattern = r'^https?:\/\/www.'
    else:
        pattern = r'^https?:\/\/'
    return re.sub(pattern, '', url)

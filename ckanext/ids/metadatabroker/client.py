import json
import logging
from typing import Set, List, Dict

import cachetools.func
import ckan.lib.dictization
import ckan.logic as logic
import rdflib

from ckanext.ids.dataspaceconnector.connector import Connector
from ckanext.ids.metadatabroker.translations_broker_ckan import URI, empty_result

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

# ToDo  Take the resource_type into account in the query
def _sparl_get_all_resources(resource_type: str):
    query = """SELECT ?resultUri ?type WHERE
    { ?resultUri a ?type }"""
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


def _to_ckan_result_format(raw_jsonld : Dict):
    g = raw_jsonld["@graph"]
    resource_graphs = [x for x in g if x["@type"]=="ids:Resource"]
    representation_graphs = [x for x in g if x["@type"]=="ids:Representation"]
    artifact_graphs = [x for x in g if x["@type"]=="ids:Artifact"]

    # ToDo get this from the central core as well
    organization_data = {
       "id": "52bc9332-2ba1-4c4f-bf85-5a141cd68423",
       "name": "orga1",
       "title": "Orga1",
       "type": "organization",
       "description": "",
       "image_url": "",
       "created": "2022-02-02T16:32:58.653424",
       "is_organization": True,
       "approval_status": "approved",
       "state": "active"
     }

    packagemeta = empty_result
    packagemeta["id"] = resource_graphs[0]["sameAs"]
    packagemeta["license_id"] = resource_graphs[0]["standardLicense"]
    packagemeta["license_url"] = resource_graphs[0]["standardLicense"]
    packagemeta["license_title"] = resource_graphs[0]["standardLicense"]
    packagemeta["metadata_created"] = resource_graphs[0]["created"]
    packagemeta["metadata_modified"] = resource_graphs[0]["modified"]
    packagemeta["name"] = resource_graphs[0]["title"]
    packagemeta["title"] = resource_graphs[0]["title"]
    packagemeta["num_resources"] = len(artifact_graphs)
    packagemeta["organization"] = organization_data
    packagemeta["owner_org"] = organization_data["id"]
    packagemeta["private"] = False
    packagemeta["type"]




@ckan.logic.side_effect_free
@cachetools.func.ttl_cache(3)  # CKan does a bunch equivalent requests in
# rapid succession
def broker_package_search(q=None, start_offset=0, fq=None):
    log.debug("\n--- STARTING  BROKER SEARCH  ----------------------------\n")
    log.debug(str(q))
    log.debug(str(fq))
    log.debug("-----------------------------------------------------------\n")
    default_search = "*:*"
    search_string = q if q is not None else default_search

    # By default we will search for all sorts of stuff
    requested_type = None
    try:
        if fq is not None:
            requested_type = [x for x in fq["fq"]
                              if x.startswith("+dataset_type")][0].split(":")[
                -1]
    except:
        pass

    log.debug("Requested search type was " + str(requested_type))
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

    log.debug("RESOURCES FOUND <------------------------------------\n")
    for ru in resource_uris:
        log.debug(ru.n3()+" <------------------------------------")
    log.debug("---------------------------||||||||||||||")

    if len(resource_uris) == 0:
        return search_results

    descriptions = {ru.n3(): connector.ask_broker_description(ru.n3()[1:-1])
                    for ru in resource_uris}

    log.debug(".\n....................................................................")
    for k,v in descriptions.items():
        log.debug(k)
        log.debug(str(v))

    log.debug(
        "\n\n....................................................................\n")



    # --------- This was an attempt to do it over SPARQL describe
    # ---------- Should be faster.. but harder to parse
    # log.info("URIs:\n"+"\n".join([x.n3() for x in resource_uris]))
    #query_for_info = _sparql_describe_many_resources(resource_uris)
    #raw_response = connector.query_broker(query_for_info)
    #all_triples = _parse_broker_tabular_response(raw_response)
    #g = listofdicts2graph(all_triples)
    #log.debug("-----INFO FROM BROKER ------------------------------")
    #rj = json.dumps(all_triples, indent=2)
    #for ru in resource_uris:
    #    r = {}
    #log.debug(rj)


    log.debug("---- END BROKER SEARCH ------------\n-----------\n----\n-----")
    return search_results

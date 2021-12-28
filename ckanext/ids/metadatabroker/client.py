import json
import logging
from typing import Set, List, Dict
import cachetools.func

import ckan.lib.dictization
import ckan.logic as logic
import rdflib

from ckanext.ids.dataspaceconnector.connector import Connector

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


def URI(somestr: str):
    if isinstance(somestr, rdflib.URIRef):
        return somestr
    if somestr.startswith("<"):
        somestr = somestr[1:]
    if somestr.endswith(">"):
        somestr = somestr[:-1]
    return rdflib.URIRef(somestr)


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
        qp += "UNION { "+ res.n3() +" ?p ?o. "
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


@ckan.logic.side_effect_free
@cachetools.func.ttl_cache(3) # CKan does a bunch equivalent requests in
# rapid succession
def broker_package_search(q=None, start_offset=0, fq=None):
    log.debug("\n--- STARTING  BROKER SEARCH  ----------------------------\n")
    default_search = "*:*"
    search_string = q if q is not None else default_search

    # By default we will search for all sorts of stuff
    requested_type = None
    try:
        if fq is not None:
            requested_type = [x for x in fq["fq"]
                          if x.startswith("+dataset_type")][0].split(":")[-1]
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

    if len(resource_uris) == 0:
        return search_results
    #log.info("URIs:\n"+"\n".join([x.n3() for x in resource_uris]))
    query_for_info = _sparql_describe_many_resources(resource_uris)
    raw_response = connector.query_broker(query_for_info)
    resource_info = _parse_broker_tabular_response(raw_response)
    resource_info_dict = _grouping_from_table_to_dict(resource_info)

    log.debug("-----INFO FROM BROKER ------------------------------")
    rj = json.dumps(resource_info, indent=2)
    log.debug(rj)
    log.debug("---- END BROKER SEARCH ------------\n-----------\n----\n-----")
    return search_results

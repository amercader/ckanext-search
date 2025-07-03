[![Tests](https://github.com//ckanext-search/workflows/Tests/badge.svg?branch=main)](https://github.com//ckanext-search/actions)

# ckanext-search


Proof of Concept for pluggable search provider and improved search capabilities in CKAN

Original discussion:

https://github.com/ckan/ckan/discussions/8444

This POC combines in a single extension code that should eventually live in different places:

* The plugin, index, cli, actions modules etc would eventually move to core
* The actual providers for Solr , Elasticsearch , etc would be separate extensions
* Search features like spatial search would live in their own relevant extension

### Requirements

There are providers for Solr and Elasticsearch.

~~For Solr you can use the CKAN Docker images:~~

Temporarily,use this Docker image:


    docker run --name ckan-solr -p 8983:8983 -d amercader/ckan-solr:2.11-solr9


For Elasticsearch:

    docker run -d --name elasticsearch --net elastic -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" elasticsearch:8.17.2

This will print the password for the `elastic` user. You also will need the CA certificates. Follow step 6 here to retrieve them:

https://www.elastic.co/guide/en/elasticsearch/reference/current/docker.html

Config options (may change):

    ckan.plugins = search search_solr search_elasticsearch

    ckan.search.search_provider = solr   # or elasticsearch

    ckan.search.solr.url = http://127.0.0.1:8983/solr/ckan2

    ckan.search.elasticsearch.url = https://localhost:9200
    ckan.search.elasticsearch.password = test1234
    ckan.search.elasticsearch.ca_certs_path = /path/to/http_ca.crt


### Backlog

Note: these are meant in the context of the proof of concept, not as final implementations.

- [x] Basic providers for Solr and Elasticsearch implementing `ISearchProvider`
- [x] Minimal indexing for datasets
- [x] Minimal querying for datasets
- [x] Support additional entity types (orgs, users, etc)
- [x] General text search across all fields
- [x] Initialize search provider: combined search schema
- [x] Initialize: setup Solr
- [x] Initialize: setup ES
- [ ] Choose what to index
- [ ] Language (stemming, etc)
- [x] `search` API params, validation
- [ ] `search` API output
- [ ] Return data_dicts vs ids or fl
- [x] Support for `_before/after_index/search` plugin hooks
- [ ] Faceting
- [ ] Error handling
- [ ] Entity specific actions (`dataset_search`, `organization_search`, etc)
- [ ] Common test suite for providers to be compliant
- [ ] `ISearchFeature` implementation
- [ ] Custom entities
- [ ] ...

Out of scope for now:

* Replacing current `package_search` usage in core
* Refactor `package_search` to use the new search implementation



## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)

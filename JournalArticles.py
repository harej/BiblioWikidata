import arrow
import html
import requests
from wikidataintegrator import wdi_core, wdi_login

def bundle_maker(biglist, size=200):
    """
    Divides a list into smaller lists

    @param biglist: A big list
    @param size: The integer representing how large each sub-list should be
    @return A list of lists that are size `size`
    """

    return [biglist[x:x+size] for x in range(0, len(biglist), size)]

def generate_refsnak(source, url, date):
    """
    Helper function to generate a reference snak.

    @param source: Wikidata ID string referring to the data source
    @param url: string of the API URL
    @param date: string of the date of access, format '+YYYY-MM-DDT00:00:00Z'
                 (precision is only to the day)

    @return one-level nested list of WD statement objects as required by
            WikidataIntegrator
    """

    return [[wdi_core.WDItemID(is_reference=True, value=source, prop_nr='P248'),
             wdi_core.WDUrl(is_reference=True, value=url, prop_nr='P854'),
             wdi_core.WDTime(is_reference=True, time=date, prop_nr='P813')]]

def issn_to_wikidata(issn):
    """
    Convert an ISSN to its Wikidata analogue, if one exists.

    @param issn: string containing the ISSN
    @return string Wikidata item ID or None if there is no match.
    """

    issn_query_url = ('https://query.wikidata.org/sparql?format=json'
                      '&query=select%20%3Fi%20%3Fissn%20where%20%7B'
                      '%20%3Fi%20wdt%3AP236%20%22{0}%22%20%7D')
    issn_query = requests.get(issn_query_url.format(issn)).json()
    issn_results = issn_query['results']['bindings']
    if len(issn_results) == 1:  # We want no ambiguity here
        journal = issn_results[0]['i']['value']
        journal = journal.replace('http://www.wikidata.org/entity/', '')
        return journal

    return None  # no match

def get_pubmed(identifiers, dbname='pubmed'):
    """
    Retrieve raw data from PubMed API. Use the `get_data` method instead if you
    want Wikidata statements created.

    @param identifiers: list of PMIDs
    @param dbname: the name of the Entrez database to use. Default is 'pubmed'
    @return dictionary of results
    """

    package = {}

    esummary_url = ('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
                    '?db={0}&retmode=json&tool=wikidata_worker'
                    '&email=jamesmhare@gmail.com&id=').format(dbname)

    bundles = bundle_maker(identifiers)

    for bundle in bundles:
        bunch_of_numbers = ''
        for pmid in bundle:
            bunch_of_numbers += pmid + ','
        bunch_of_numbers = bunch_of_numbers[:-1]  # Remove trailing comma

        summary_retriever = requests.get(esummary_url + bunch_of_numbers).json()

        if "result" in summary_retriever_json:
            for _, pmid_blob in summary_retriever_json["result"].items():
                if _ == "uids":
                    continue

                pmid = pmid_blob["uid"]
                package[pmid] = pmid_blob
                package[pmid]['__querydate'] = '+' + arrow.utcnow().format('YYYY-MM-DD') \
                                             + 'T00:00:00Z'

    return package

def get_pubmed_central(identifiers):
    """
    Retrieve raw data from PMC API. Use the `get_data` method instead if you
    want Wikidata statements created.

    @param identifiers: list of PMCIDs
    @return dictionary of results
    """

    return get_pubmed(identifiers, dbname='pmc')

def get_doi_org(identifiers):
    """
    Retrieve raw data from DOI.org. Use the `get_data` method instead if you
    want Wikidata statements created.

    @param identifiers: list of DOIs
    @return dictionary of results
    """

    package = {}

    headers = {"Accept": "application/json"}
    for doi in identifiers:
        r = requests.get('https://doi.org/' + doi, headers=headers)

        if r.status_code != 200:
            continue

        try:
            package[doi] = r.json()
        except:
            continue

        package[doi]['__querydate'] = '+' + arrow.utcnow().format('YYYY-MM-DD') \
                                    + 'T00:00:00Z'

    return package

def get_data(manifest):
    """
    Method to retrieve data from PubMed, PubMed Central, and DOI.org databases.

    Have at least one of a DOI, PMCID, or PMID in each dictionary. From there,
    this method will query some friendly databases. You can also specify other
    Wikidata statements to add.

    @param manifest: a list of dictionaries, with the following keys and values:
                        doi:   string or None
                        pmcid: string or None
                        pmid:  string or None
                        data:  list of additional WDI objects (WDString etc.) to
                               incorporate into the output, or empty list
    @return list of Wikidata statement objects.
    """

    # To prevent weirdness from unexpected values
    for entry in manifest:
        for thing in entry.keys():
            if thing not in ['pmid', 'pmcid', 'doi', 'data']:
                raise ValueError('The only permitted keys are doi, pmcid, pmid, and data')

    months = {
        'Jan': '01',
        'Feb': '02',
        'Mar': '03',
        'Apr': '04',
        'May': '05',
        'Jun': '06',
        'Jul': '07',
        'Aug': '08',
        'Sep': '09',
        'Oct': '10',
        'Nov': '11',
        'Dec': '12'}

    # Initializing package, a list of objects containing a list of Wikidata item
    # objects and an object containing raw data. Each object in the package list
    # corresponds to the list entry in manifest.

    package = []

    lookup = {'pmid': [], 'pmcid': [], 'doi': []}

    # Associates an identifier with a given manifest/package entry
    associator = {'pmid': {}, 'pmcid': {}, 'doi': {}}

    counter = 0
    for entry in manifest:
        if 'data' not in entry:
            statements = []
        else:
            statements = entry['data']

        # Instance of: scientific article
        statements.append(wdi_core.WDItemID(value='Q180686', prop_nr='P31'))

        if 'pmid' in entry:
            if 'pmid' is not None:
                statements.append(wdi_core.WDString(value=entry['pmid'], prop_nr='P698'))

        if 'pmcid' in entry:
            if 'pmcid' is not None:
                statements.append(wdi_core.WDString(value=entry['pmcid'], prop_nr='P932'))

        if 'doi' in entry:
            if 'doi' is not None:
                statements.append(wdi_core.WDString(value=entry['doi'], prop_nr='P356'))

        package.append({'statements': statements, 'raw_data': {}, 'label': ''})

        # Append to the lookup lists. API lookups are done in bulk to cut down
        # on HTTP requests.
        for id_name, id_value in entry.items():
            if id_name != 'doi' and 'doi' in entry:
                continue  #
            if id_name == 'pmcid' and 'pmid' in entry:
                continue  # we don't need pmcid if we already have pmid
            lookup[id_name].append(id_value)
            associator[id_name][id_value] = counter

        counter += 1

    raw_data = {}
    raw_data['pmid'] = get_pubmed(lookup['pmid'])
    raw_data['pmcid'] = get_pubmed_central(lookup['pmcid'])
    raw_data['doi'] = get_doi_org(lookup['doi'])

    # Now that the requests are done, we want to painstakingly re-associate each
    # result object with the corresponding list in the package. This is mostly
    # to keep me from going crazy.

    for data_source, data_object in raw_data.items():
        for identifier, result in data_object.items():
            index = associator[data_source][identifier]
            package[index]['raw_data'][data_source] = result

    counter = 0
    for entry in package:

        # We only query PubMed in one place of two. It's basically the same API
        # but drawing from a different dataset.
        pubmed_data = {}
        if 'pmcid' in entry['raw_data']:
            pubmed_data_source = ('pmc', 'Q229883')  # for use in refsnak generator
            pubmed_data = entry['raw_data']['pmcid']
        elif 'pmid' in entry['raw_data']:
            pubmed_data_source = ('pubmed', 'Q180686')
            pubmed_data = entry['raw_data']['pmid']

        doi_data = {}
        if 'doi' in entry['raw_data']:
            doi_data = entry['raw_data']['doi']

        # If we have data from both PubMed and DOI.org, we are interested in
        # both. PubMed/PubMed Central has article IDs, while DOI.org has better
        # author names and better data overall.

        # Initializing statement variables to prevent duplication/overwrites.
        statement_title = None
        statement_doi = None
        statement_pmid = None
        statement_pmcid = None
        statement_pubdate = None
        statement_publishedin = None
        statement_volume = None
        statement_issue = None
        statement_pages = None
        statement_origlanguage = None
        statement_authors = []

        if doi_data != {}:
            doi_ref = generate_refsnak(
                          'Q28946522',
                          'https://doi.org/' + manifest[counter]['doi'],
                          doi_data['__querydate'])

            if 'title' in doi_data and statement_title is None:
                statement_title = wdi_core.WDMonolingualText(
                                      value=doi_data['title'],
                                      prop_nr='P1476',
                                      references=doi_ref,
                                      language='en')
                package[counter]['statements'].append(statement_title)
                package[counter]['label'] = doi_data['title']

            if 'DOI' in doi_data and statement_doi is None:
                statement_doi = wdi_core.WDString(
                                    value=doi_data['DOI'],
                                    prop_nr='P356',
                                    references=doi_ref)
                package[counter]['statements'].append(statement_doi)

            if 'created' in doi_data and statement_pubdate is None:
                to_add = doi_data['created']['date-time'].split('T')[0]
                statement_pubdate = wdi_core.WDTime(
                                        value=to_add,
                                        prop_nr='P577',
                                        references=doi_ref)
                package[counter]['statements'].append(statement_pubdate)

            if 'ISSN' in doi_data and statement_publishedin is None:
                journal = issn_to_wikidata(doi_data['ISSN'][0])
                if journal is not None:
                    statement_publishedin = wdi_core.WDItemID(
                                                value=journal,
                                                prop_nr='P1433',
                                                references=doi_ref)
                    package[counter]['statements'].append(statement_publishedin)

            if 'volume' in doi_data and statement_volume is None:
                statement_volume = wdi_core.WDString(
                                       value=doi_data['volume'],
                                       prop_nr='P478',
                                       references=doi_ref)
                package[counter]['statements'].append(statement_volume)

            if 'issue' in doi_data and statement_issue is None:
                statement_issue = wdi_core.WDString(
                                      value=doi_data['issue'],
                                      prop_nr='P433',
                                      references=doi_ref)
                package[counter]['statements'].append(statement_issue)

            if 'author' in doi_data and statement_authors == []:
                author_counter = 0
                for author in doi_data['author']:
                    author_counter += 1
                    a = ''
                    if 'family' in author:
                        a = author['family']
                    if 'given' in author:
                        a = author['given'] + ' ' + a

                    qualifier = wdi_core.WDString(
                                    value=str(author_counter),
                                    prop_nr='P1545',
                                    is_qualifier=True)
                    statement_author = wdi_core.WDString(
                                           value=a,
                                           prop_nr='P2093',
                                           qualifiers=[qualifier],
                                           references=doi_ref)
                    statement_authors.append(statement_author)
                for statement in statement_authors:
                    package[counter]['statements'].append(statement)

        if pubmed_data != {}:
            u = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db={0}&retmode=json&id={1}'
            pubmed_ref = generate_refsnak(
                             pubmed_data_source[1],
                             u.format(pubmed_data_source[0],
                             pubmed_data['uid']),
                             pubmed_data['__querydate'])

            if 'title' in pubmed_data and statement_title is None:
                t = html.unescape(pubmed_data['title'])
                if t != '':
                    if t[-1:] == '.':
                        t = t[:-1]
                    if t[0] == '[' and t[-1:] == ']':
                        t = t[1:-1]

                    # Strip HTML tags
                    t = re.sub(r'\</?(.|sub|sup)\>', '', t)

                    # After all processing is done:
                    statement_title = wdi_core.WDMonolingualText(
                                          value=t,
                                          prop_nr='P1476',
                                          references=pubmed_ref,
                                          language='en')
                    package[counter]['statements'].append(statement_title)
                    package[counter]['label'] = t

            if 'articleids' in pubmed_data:
                for block in pubmed_data['articleids']:
                    if block['idtype'] == 'pmc' and statement_pmcid is None:
                        pmcid = block['value'].replace('PMC', '')
                        statement_pmcid = wdi_core.WDString(
                                              value=pmcid,
                                              prop_nr='P932',
                                              references=pubmed_ref)
                        package[counter]['statements'].append(statement_pmcid)
                    elif block['idtype'] == 'pmcid' and statement_pmcid is None:
                        pmcid = block['value'].replace('PMC', '')
                        statement_pmcid = wdi_core.WDString(
                                              value=pmcid,
                                              prop_nr='P932',
                                              references=pubmed_ref)
                        package[counter]['statements'].append(statement_pmcid)
                    elif block['idtype'] == 'doi' and statement_doi is None:
                        doi = block['value']
                        statement_doi = wdi_core.WDString(
                                            value=doi,
                                            prop_nr='P356',
                                            references=pubmed_ref)
                        package[counter]['statements'].append(statement_doi)
                    elif block['idtype'] in ['pmid', 'pubmed'] and statement_pmid is None:
                        pmid = block['value']
                        statement_pmid = wdi_core.WDString(
                                             value=pmid,
                                             prop_nr='P698',
                                             references=pubmed_ref)
                        package[counter]['statements'].append(statement_pmid)

            if 'pubdate' in pubmed_data and statement_pubdate is None:
                pubdate = None
                precision = None
                pubdate_raw = pubmed_data['pubdate'].split(' ')  # 2016 Aug 1
                if len(pubdate_raw) > 1:
                    if pubdate_raw[1] in months:
                        m = months[pubdate_raw[1]]
                    else:
                        m = '00'
                if len(pubdate_raw) == 3:  # Precision to the day
                    pubdate = "+{0}-{1}-{2}T00:00:00Z".format(
                                  pubdate_raw[0],
                                  m,
                                  pubdate_raw[2].zfill(2))
                    precision = 11
                elif len(pubdate_raw) == 2:  # Precision to the month
                    pubdate = "+{0}-{1}-00T00:00:00Z".format(
                                  pubdate_raw[0],
                                  m)
                    precision = 10
                elif len(pubdate_raw) == 1:  # Precision to the year
                    pubdate = "+{0}-00-00T00:00:00Z".format(
                                  pubdate_raw[0])
                    precision = 9

                if pubdate is not None and precision is not None:
                    statement_pubdate = wdi_core.WDTime(
                                            value=pubdate,
                                            precision=precision,
                                            prop_nr='P577',
                                            references=pubmed_ref)
                    package[counter]['statements'].append(statement_pubdate)

            if 'issn' in pubmed_data and statement_publishedin is None:
                if pubmed_data['issn'] != '':
                    journal = issn_to_wikidata(pubmed_data['issn'])
                    if journal is not None:
                        statement_publishedin = wdi_core.WDItemID(
                                                    value=journal,
                                                    prop_nr='P1433',
                                                    references=pubmed_ref)
                        package[counter]['statements'].append(statement_publishedin)

            if 'volume' in pubmed_data and statement_volume is None:
                if pubmed_data['volume'] != '':
                    statement_volume = wdi_core.WDString(
                                           value=pubmed_data['volume'],
                                           prop_nr='P478',
                                           references=pubmed_ref)
                    package[counter]['statements'].append(statement_volume)

            if 'issue' in pubmed_data and statement_issue is None:
                if pubmed_data['issue'] != '':
                    statement_issue = wdi_core.WDString(
                                          value=pubmed_data['issue'],
                                          prop_nr='P433',
                                          references=pubmed_ref)
                    package[counter]['statements'].append(statement_issue)

            if 'pages' in pubmed_data and statement_pages is None:
                if pubmed_data['pages'] != '':
                    statement_pages = wdi_core.WDString(
                                          value=pubmed_data['pages'],
                                          prop_nr='P304',
                                          references=pubmed_ref)
                    package[counter]['statements'].append(statement_pages)

            if 'lang' in pubmed_data and statement_origlanguage is None:
                for langcode in pubmed_data['lang']:
                    # Please post a comment on this webzone if you know the
                    # other possible values for 'lang'
                    if langcode == 'eng':
                        statement_origlanguage = wdi_core.WDItemID(
                                                     value='Q1860',
                                                     prop_nr='P364',
                                                     references=pubmed_ref)
                        package[counter]['statements'].append(statement_origlanguage)

            if 'authors' in pubmed_data and statement_authors == []:
                author_counter = 0
                for author in pubmed_data['authors']:
                    if author['authtype'] == "Author":
                        author_counter += 1
                        qualifier = wdi_core.WDString(
                                        value=str(author_counter),
                                        prop_nr='P1545',
                                        is_qualifier=True)
                        statement_author = wdi_core.WDString(
                                               value=author['name'],
                                               prop_nr='P2093',
                                               qualifiers=[qualifier],
                                               references=doi_ref)
                        statement_authors.append(statement_author)
                for statement in statement_authors:
                    package[counter]['statements'].append(statement)

        counter += 1

    return package

def item_creator(manifest):
    """
    Method for creating new Wikidata items on journal articles.

    This does *not* handle de-duplication! Make sure you filter out already-
    existing items before passing them through this method.

    @param manifest: a list of dictionaries, with the following keys and values:
                        doi:   string or None
                        pmcid: string or None
                        pmid:  string or None
                        data:  list of additional WDI objects (WDString etc.) to
                               add to the new item, or empty list
    """

    retrieved_data = get_data(manifest)

    for new_entry in retrieved_data:
        data = new_entry['statements']
        label = new_entry['label']
        i = wdi_core.WDItemEngine(data=data, item_name=label)
        try:
            i.write(WIKI_SESSION)
        except Exception as e:
            print(e)
            continue

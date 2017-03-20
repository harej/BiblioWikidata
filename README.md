Scripts for integrating bibliographic metadata into Wikidata from various sources, currently including PubMed, PubMed Central, and the DOI.org endpoint. Other APIs and datasets will be included in the future.

# Requirements

Python 3.5 or higher is required.

This makes use of the WikidataIntegrator library. You can easily install it with `pip3 install wikidataintegrator`.

# Usage

There are docstrings throughout the code files. You may peruse those.

But generally, the only thing that's really been implemented at the moment is the ability to create new Wikidata items in bulk.

Sample program: You have a list of DOIs saved at `doi_list.csv`.

```python
import csv
from BiblioWikidata import JournalArticles

def main():

	# Load the DOIs from file. VERY IMPORTANT: BiblioWikidata does *not* check
	# your list against Wikidata for existing entries! You must do this first.

	list_of_DOIs = []
	with open('doi_list.csv') as f:
		spreadsheet = csv.reader(f)  # One-column CSV of DOI strings
		for row in spreadsheet:
			list_of_DOIs.append(row[0])

	# Construct the "manifest"
	# The manifest is a list of dictionaries. The dictionaries have a syntax
	# like this:
	#
	#     {'doi': '10.100/abc', 'pmid': '1234', 'pmcid': '5678'}
	#
	# The PMIDs and PMCIDs are strings, and the PMCID string does not include
	# the 'PMC' prefix.
	#
	# You may optionally include a 'data' parameter including a list of Wikidata
	# statements you want to include in addition to the data generated by the
	# BiblioWikidata library. These statements must take the form of `WDBaseDataType`
	# children.

	manifest = [{'doi': x} for x in list_of_DOIs]

	JournalArticles.item_creator(manifest)
```
# restaurant2osm
Mattilsynet publishes their restaurant inspections on a REST service. This program loads the inspection data from the REST service and extacts the restaurants.

### Usage ###

<code>python restaurant2osm.py [filter]</code>

All filters from the REST service are permitted, plus one extra filter for municipality. Examples:
* One municipality: <code>"kommune=Nes (Akershus)"</code> (include county name and "" if municipality name is not unique)
* One post code name: <code>"poststed=Vang på Hedmarken"</code> (include full name if not unique)
* One post code: <code>postnr=4885</code>
* Restaurant name: <code>navn=Egon</code> (matches complete words only)
* General queries: <code>query=Torvet</code> (matches complete words in any attribute, e.g. name and address)
* Also combinations: <code>"query=Egon&poststed=Oslo"</code> (please include "")

### Notes ###

* Addresses are geocoded using Kartverket REST service from the cadastral register
* Mattilsynet is using internal addresses, many of which are not correct or incomplete
* If no match, a few corrections are tried (removing abbreviations etc)
* Addresses which are not possible to geocode to an exact location get a (0,0) coordinate and a GEOCODE tag. The output file may be processed further with [geocode2osm](https://github.com/osmno/geocode2osm) to locate the missing addresses.
* Default tagging is *amenity=restaurant*. Some nodes get *amenity=cafe*, *amenity=fast_food* or *shop=bakery* based on their names. The tagging needs one by one verification.
* Restaurant names are not copy-edited - alle names need manual verification.
* Some restaurants have a short lifespan. Please see the provided date for last inspection. Mattilsynet targets 12 months inspection intervals.
* Please see the provided date of creation to find the most recent/new restaurants.


### References ###

* [Mattilsynet REST description](https://data.norge.no/data/mattilsynet/smilefjestilsyn-på-serveringssteder)
* [Mattilsynet REST search page](https://hotell.difi.no/?dataset=mattilsynet/smilefjes/tilsyn)
* [Kartverket address REST description](https://ws.geonorge.no/adresser/v1/)

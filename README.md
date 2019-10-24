# restaurant2osm

Mattilsynet publishes their restaurant inspections on a REST service. This program loads the inspection data from the REST service and extacts the restaurants.

## Usage

```python
python restaurant2osm.py [filter][first inspection date]
```

All filters from the REST service are permitted, plus one extra filter for municipality. Examples:

- One municipality: `"kommune=Nes (Akershus)"` (include county name and "" if municipality name is not unique)
- One post code name: `"poststed=Vang på Hedmarken"` (include full name if not unique)
- One post code: `postnr=4885`
- Restaurant name: `navn=Egon` (matches complete words only)
- General queries: `query=Torvet` (matches complete words in any attribute, e.g. name and address)
- Also combinations: `"query=Egon&poststed=Oslo"` (please include "")

The optional second parameter will produce restaurants with first inspection date on or after the given date. Format: 2019-10-15.

## Notes

- Addresses are geocoded using Kartverket REST service from the cadastral register
- Mattilsynet is using internal addresses, many of which are not correct or incomplete
- If no match, a few corrections are tried (removing abbreviations etc)
- Addresses which are not possible to geocode to an exact location get a (0,0) coordinate and a GEOCODE tag. The output file may be processed further with [geocode2osm](https://github.com/osmno/geocode2osm) to locate the missing addresses.
- Default tagging is _amenity=restaurant_. Some nodes get _amenity=cafe_, _amenity=fast_food_ or _shop=bakery_ based on their names. The tagging needs one by one verification.
- Restaurant names are not copy-edited - alle names need manual verification.
- Some restaurants have a short lifespan. Please see the provided date for last inspection. Mattilsynet targets 12 months inspection intervals.
- Please see the provided _date of creation_ or _first inspection date_ to find the most recent/new restaurants.
- Please use the provided _municipality_ or _county_ to search for specific geographical areas.
- A ready to use OSM file is provided [here](https://drive.google.com/drive/folders/1nhxjciiwOOIWmTlmXsQp-4WoYwZlsGZ6?usp=sharing).

## Importing the data into OSM

1. Open [JOSM](https://josm.openstreetmap.de/) and activate [Expert Mode](https://josm.openstreetmap.de/wiki/Help/ExpertMode) to be able to download data from the Overpass API
2. Download a new layer from overpass with this query

```overpassql
[out:json][timeout:25];
{{geocodeArea:bergen}}->.searchArea;
(
  nwr["amenity"="cafe"](area.searchArea);
  nwr["amenity"="restaurant"](area.searchArea);
  nwr["amenity"="fast_food"](area.searchArea);
  nwr["tourism"="hotel"](area.searchArea);
  nwr["tourism"="bakery"](area.searchArea);
);
out body;
>;
out skel qt;
```

3. Load the output file generated from restaurants2osm.py into JOSM and start comparing them, either by copying everything in one layer over to the other or by using [Conflation](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/Conflation)

## References

- [Mattilsynet REST description](https://data.norge.no/data/mattilsynet/smilefjestilsyn-på-serveringssteder)
- [Mattilsynet REST search page](https://hotell.difi.no/?dataset=mattilsynet/smilefjes/tilsyn)
- [Kartverket address REST description](https://ws.geonorge.no/adresser/v1/)
- [Ready-to-use OSM file](https://drive.google.com/drive/folders/1nhxjciiwOOIWmTlmXsQp-4WoYwZlsGZ6?usp=sharing)

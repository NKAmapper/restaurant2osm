# restaurant2osm

Mattilsynet makes their restaurant inspections available as open data. This program loads the inspection data from Mattilsynet and extacts the restaurants.

## Usage

```python
python restaurant2osm.py [first inspection date]
```

The optional second parameter will produce restaurants with first inspection date on or after the given date. Format: 2019-10-15.

## Notes

- Addresses are geocoded using the Kartverket REST service from the cadastral register.
- Geocoding from last run in the file _restaurants.osm_ is reused for speeding up the geocoding process by several hours.
- Mattilsynet is using internal addresses, many of which are not correct or incomplete.
- If no match, a few corrections are tried (removing abbreviations etc).
- Addresses which can not be geocoded to an exact location get a (0,0) coordinate and a GEOCODE tag. The output file may be processed further with [geocode2osm](https://github.com/osmno/geocode2osm) to locate the missing addresses.
- Default tagging is _amenity=restaurant_. Some nodes get _amenity=cafe_, _amenity=fast_food_ or _shop=bakery_ based on their names. The tagging needs one by one verification.
- Restaurant names are not copy-edited - all names need to be manually verified.
- Some restaurants have a short lifespan. Please see the provided date for last inspection. Mattilsynet targets 12 months inspection intervals, but 24 months intervals frequently occures.
- Please see the provided _date of creation_ or _first inspection date_ to find the most recent/new restaurants.
- Please use the provided _municipality_ or _county_ to search for specific geographical areas.
- A ready to use OSM file is provided [here](https://www.jottacloud.com/s/059f4e21889c60d4e4aaa64cc857322b134).

## References

- [About Mattilsynet inspections](https://www.mattilsynet.no/mat-og-drikke/forbrukere/smilefjesordningen)
- [Kartverket address REST description](https://ws.geonorge.no/adresser/v1/)
- [Ready-to-use OSM file](https://drive.google.com/drive/folders/1nhxjciiwOOIWmTlmXsQp-4WoYwZlsGZ6?usp=sharing)

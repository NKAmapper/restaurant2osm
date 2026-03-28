#!/usr/bin/env python3
# -*- coding: utf8

# restaurant2osm
# Extracts restaurants from Mattilsynet inspections and produces OSM file for import/update
# Usage: restaurant2osm [first inspection date]
# The program produces restaurants which have their first inspection date on or after the given optional parameter
# Writes output file to "restaurants.osm"
# Reads postal/municipality codes from Posten and counties from Kartverket


import json
import html
import sys
import time
import csv
import urllib.request, urllib.parse, urllib.error
import re
import os.path
from io import TextIOWrapper
from xml.etree import ElementTree


version = "1.2.0"

header = { "User-Agent": "osm-no/restaurant2osm" }

osm_filename = "restaurants.osm"

geocode_address = True  # True to geocode addresses, else get empty coordinates (0, 0)

debug = True

max_restaurants = 100000

transform_name = {
	'AMFI': 'Amfi',
	'Gate': 'gate',
	'I': 'i',
	'IKEA': 'Ikea',
	'McDonald': "McDonald's",
	'McDonalds': "McDonald's",
	"Mcdonald'S": "McDonald's",
	'Og': 'og',
	'På': 'på',
	'Avdeling': '',
	'avdeling': '',
	'AVD.': '',
	'AVD': '',
	'Avd.': '',
	'avd.': '',
	'Avd': '',
	'avd': '',
	'AS': '',
	'As': '',
	'as': '',
	'A/S': '',
	'a/s': '',
	'A.S:': '',
	'a.s.': '',
	'As.': '',
	'as.': '',
	'A.S': '',
	'a.s': '',
	'D/A': '',
	'L/L': '',
	'LL': '',
	'A/L': '',
	'ANS': '',
	'ans': '',
	'DA': '',
	'Invest': '',
	'invest': '',
	'DRIFT': '',
	'Drift': '',
	'drift': ''
}

transform_address = {
	'sgate ': 's gate ',
	'sgt ': 's gate ',
	'sgt.': 's gate',
	'sveg ': 's veg ',
	'svei ': 's vei ',
	'splass ': 'splass ',
	'storg ': 's torg ',
	'storv ': 's torv ',
	'sbrygge ': 's brygge ',
	'gt ': 'gate ',
	'gt.': 'gate ',
	'pl.': 'plass ',
	'pl ': 'plass ',
	'br.': 'brygge ',
	'v.': 'vei ',
	'vn.': 'veien',
	'è': 'é'
}

amenities = {
	'kafe': 'cafe',
	'cafe': 'cafe',
	'kafé': 'cafe',
	'café': 'cafe',
	'kaffe': 'cafe',
	'coffee': 'cafe',
	'espresso': 'cafe',
	'baker': 'bakery',
	'brød': 'bakery',
	'kafeteria': 'cafe',
	'konditori': 'cafe',
	'conditori': 'cafe',
	'kiosk': 'cafe',
	'iskrembar': 'cafe',
	'juice': 'cafe',
	'hotel': 'hotel',
	'Staarbucks': 'cafe',
	'Jordbærpikene': 'cafe',
	'burger': 'fast_food',
	'kebab': 'fast_food',
	'Subway': 'fast_food',
	'gatekjøkken': 'fast_food',
	'McDonald': 'fast_food',
	'Mc Donald': 'fast_food',
	'Burger King': 'fast_food'
}



# Produce a tag for OSM file

def make_osm_line(key,value):

	global file

	if value:
		encoded_value = html.escape(value).strip()
		file.write ('    <tag k="' + key + '" v="' + encoded_value + '" />\n')



# Output message

def message (line):

	sys.stdout.write (line)
	sys.stdout.flush()



# Open file/api, try up to 5 times, each time with double sleep time

def try_urlopen (url):

	tries = 0
	while tries < 5:
		try:
			return urllib.request.urlopen(url)

		except urllib.error.HTTPError as e:
			if tries  == 0:
				message ("\n") 
			message ("\r\tHTTP error %i %s. Retry %i in %ss... " % (e.code, e.reason, tries + 1, 5 * (2**tries)))
			time.sleep(5 * (2**tries))
			tries += 1
			error = e

#		except urllib.error.URLError as e:  # Mostly "Connection reset by peer"
	
	message ("\n\nError: %s\n" % error.reason)
	message ("%s\n\n" % url.get_full_url())
	sys.exit()



# Concatenate address line

def get_address(street, house_number, postal_code, city):

	address = street

	if house_number:
		address = address + " " + house_number

	if address:
		address = address + ", "

	if postal_code:
		address = address + postal_code + " "

	if city:
		address = address + city

	return address.strip()



# Geocoding with Kartverket Matrikkel/Vegnavn REST service

def geocode (street, house_number, house_letter, city):

#	time.sleep(1)

	if house_number:

		if street[-1] == "-":  # Avoid Kartverket bug
			street = street[0: len(street) - 1]
		if ":" in street:
			street = street.replace(":", " ").replace("  ", " ")

		if house_letter:
			url = "https://ws.geonorge.no/adresser/v1/sok?sok=%s&nummer=%s&bokstav=%s&poststed=%s&treffPerSide=10" %\
					 (urllib.parse.quote(street), house_number, house_letter, urllib.parse.quote(city))
		else:
			url = "https://ws.geonorge.no/adresser/v1/sok?sok=%s&nummer=%s&poststed=%s&treffPerSide=10" %\
					 (urllib.parse.quote(street), house_number, urllib.parse.quote(city))

		request = urllib.request.Request(url)
		file = try_urlopen(request)
		result = json.load(file)
		file.close()

		result = result['adresser']

		if result:
			latitude = result[0]['representasjonspunkt']['lat']
			longitude = result[0]['representasjonspunkt']['lon']
			return (latitude, longitude)
		else:
			return None

	else:
		return None



# Main program

if __name__ == '__main__':

	message ("\nRestaurants from Mattilsynet inspections\n")

	if len(sys.argv) > 1:
		input_date = sys.argv[1]
	else:
		input_date = "1900-01-01"

	# Read county names

	filename = "https://ws.geonorge.no/kommuneinfo/v1/fylker"
	file = urllib.request.urlopen(filename)
	county_data = json.load(file)
	file.close()

	county_names = {}
	for county in county_data:
		county_names[county['fylkesnummer']] = county['fylkesnavn'].strip()

	# Read postal codes and municipality codes from Posten (updated daily). Windows-1252 coding.

	file = urllib.request.urlopen('https://www.bring.no/postnummerregister-ansi.txt')
	postal_codes = csv.DictReader(TextIOWrapper(file, "windows-1252"), fieldnames=['zip','post_city','municipality_ref','municipality_name','type'], delimiter="\t")
	postcode_districts = {}
	for row in postal_codes:
		postcode_districts[ row['zip'] ] = {
			'city': row['post_city'].strip().title(),
			'municipality_ref': row['municipality_ref'],
			'municipality_name': row['municipality_name'].strip().title()
		}
	file.close()


	# Load OSM file from previous run

	message ("\nLoading previous restaurants from '%s' file... " % osm_filename)

	old_restaurants = {}

	if os.path.isfile(osm_filename):

		tree = ElementTree.parse(osm_filename)
		root = tree.getroot()

		count_all = 0
		count_old = 0

		for node in root.iter('node'):

			count_all += 1
			ref_tag = node.find("tag[@k='ref:mattilsynet']")
			if ref_tag != None:
				ref = ref_tag.get("v")
				latitude = float(node.get("lat"))
				longitude = float(node.get("lon"))
				if latitude != 0.0 and longitude != 0.0:
					old_restaurants[ref] = {
						'latitude': latitude,
						'longitude': longitude
					}

					geocode_tag = node.find("tag[@k='GEOMETHOD']")
					if geocode_tag != None:
						old_restaurants[ref]['geocode_method'] = geocode_tag.get("v")

					geocode_tag = node.find("tag[@k='GEORESULT']")
					if geocode_tag != None:
						old_restaurants[ref]['geocode_result'] = geocode_tag.get("v")

					count_old += 1

		message ("\nFound %i of %i restaurants with coordinates\n" % (count_old, count_all))

	else:
		message ("\nNo such file found, creating file for all restaurants from scratch\n")


	# Load all inspections from Mattilsynet

	message ("\nLoading inspections from Mattilsynet... ")

	restaurants = []
	total_restaurants = 0
	unique_restaurants = 0

	url = "https://matnyttig.mattilsynet.no/smilefjes/tilsyn.csv"
	request = urllib.request.Request(url)  #, headers=header)
	file = urllib.request.urlopen(request)

	csv_reader = csv.DictReader(TextIOWrapper(file), delimiter=";")

	for inspection in csv_reader:  # Iterate all inspections on result page

		entry = {}

		# Fix name

		name = inspection['navn']
		if name == name.upper():
			name = name.title()
		name_split = name.split()
		name = ""
		for word in name_split:  # [1:]:
			new_word = word
			for word_from, word_to in iter(transform_name.items()):
				if word == word_from or word == word_from + "," or word == word_from + "-":
					new_word = new_word.replace(word_from, word_to)
			name += new_word + " "
		name = name.replace("è", "é").replace("`", "'").replace("´", "'")
		name = name.replace("  "," ").replace("  ", " ").replace(" ,", ",").strip(",").strip("-").strip("/").strip()
		if len(name) > 1:
			name = name[0].upper() + name[1:]

		date_inspection = "%s-%s-%s" % (inspection['dato'][4:8], inspection['dato'][2:4], inspection['dato'][0:2])

		entry['ref'] = inspection['tilsynsobjektid'].replace("_Tilsynsobjekt", "")  #[1:20]  #[20:25]
		entry['orgnr'] = inspection['orgnummer']
		entry['name'] = name
		entry['original_name'] = inspection['navn'].strip()
		entry['postcode'] = inspection['postnr']
		entry['city'] = inspection['poststed'].strip()
		entry['date_first_inspection'] = date_inspection
		entry['date_last_inspection'] = date_inspection
		entry['date_created'] = "20%s-%s-%s" % \
					(inspection['tilsynsobjektid'][1:3], inspection['tilsynsobjektid'][3:5], inspection['tilsynsobjektid'][5:7])

		street = inspection['adrlinje1'].strip()
		original_street = street
		if inspection['adrlinje2']:
			street = inspection['adrlinje2'].strip()
			original_street = original_street + ", " + inspection['adrlinje2'].strip()

		# Find house number and unit/letter

		reg = re.search(r'(.*) [0-9]+[ \-\/]+([0-9]+)[ ]*([A-Za-z]?)$', street)
		if not(reg):
			reg = re.search(r'(.*) ([0-9]+)[ ]*([A-Za-z]?)$', street)				
		if reg:
			street = reg.group(1).strip()
			house_number = reg.group(2)
			house_letter = reg.group(3)
		else:
			house_number = ""
			house_letter = ""

		address = get_address(street, house_number + house_letter, entry['postcode'], entry['city'])

		entry['street'] = street
		entry['house_number'] = house_number
		entry['house_letter'] = house_letter
		entry['address'] = address
		entry['original_address'] = get_address(original_street, "", inspection['postnr'], inspection['poststed'])

		# Look up identical previous restaurants to avoid duplicates

		found = None
		for previous in restaurants:
			if (previous['address'] == address) and (previous['original_name'] == entry['original_name']):
				found = previous

		if found:
			if found['date_last_inspection'] < date_inspection:
				found['date_last_inspection'] = date_inspection
			if found['date_first_inspection'] > date_inspection:
				found['date_first_inspection'] = date_inspection

		elif " M/S" not in name and "M/S " not in name and "MS " not in name and "MF " not in name and "M/F " not in name:  # Avoid ships
			restaurants.append(entry)
			unique_restaurants += 1

		total_restaurants += 1

	file.close()


	# Update dates for reporting

	latest_inspection = ""
	first_inspection = "9999"
	latest_restaurant = ""
	
	for restaurant in restaurants:
		if restaurant['date_last_inspection'] > latest_inspection:
			latest_inspection = restaurant['date_last_inspection']
		if restaurant['date_first_inspection'] < first_inspection:
			first_inspection = restaurant['date_first_inspection']
		if restaurant['date_created'] > latest_restaurant:
			latest_restaurant = restaurant['date_created']

	message ("\nFound %i inspections and %i restaurants\n\n" % (total_restaurants, unique_restaurants))


	# Produce OSM file

	count_new = 0
	count_old = 0
	count_output = 0

	if (unique_restaurants > 0) and (unique_restaurants < max_restaurants):

		# Produce OSM file header

		message ("Geocoding and generating output file...\n")

		filename = osm_filename.replace(".osm", "_new.osm")
		file = open (filename, "w")
		file.write ('<?xml version="1.0" encoding="UTF-8"?>\n')
		file.write ('<osm version="0.6" generator="restaurant2osm v%s" upload="false">\n' % version)

		node_id = -10000

		# Iterate all restaurants and produce OSM tags

		for restaurant in restaurants:

			if restaurant['date_first_inspection'] >= input_date:

				# Attempt to geocode address

				latitude = 0.0
				longitude = 0.0
				result = False

				if restaurant['ref'] in old_restaurants:
					latitude = old_restaurants[ restaurant['ref'] ]['latitude']
					longitude = old_restaurants[ restaurant['ref'] ]['longitude']
					result = True
					count_old += 1

				elif geocode_address:
					result = geocode (restaurant['street'], restaurant['house_number'], restaurant['house_letter'], restaurant['city'])

					if result:
						latitude = result[0]
						longitude = result[1]
						count_new += 1

					else:
						# Attempt new geocoding after fixing street name

						street = restaurant['street'] + " "
						old_street = street
						for word_from, word_to in iter(transform_address.items()):
							street = street.replace(word_from, word_to)
							street = street.replace(word_from.upper(), word_to.upper())

						if street != old_street:
							result = geocode (street, restaurant['house_number'], restaurant['house_letter'], restaurant['city'])
							if result:
								latitude = result[0]
								longitude = result[1]
								count_new += 1

				node_id -= 1
				count_output += 1

				file.write ('  <node id="%i" lat="%f" lon="%f">\n' % (node_id, latitude, longitude))

				# Decide amenity type

				amenity = "restaurant"
				for keyword, amenity_value in iter(amenities.items()):
					if keyword.lower() in restaurant['name'].lower():
						amenity = amenity_value

				# Produce tags

				if amenity == "hotel":
					make_osm_line("amenity", "restaurant")
					make_osm_line("FIXME", "Please consider tourism=hotel tagging, or separate node")
				elif amenity == "bakery":
					make_osm_line("amenity", "cafe")
					make_osm_line("shop", "bakery")
				else:
					make_osm_line("amenity", amenity)

				make_osm_line("ref:mattilsynet", restaurant['ref'])
#				make_osm_line("ref:orgnr", restaurant['orgnr'])
				make_osm_line("name", restaurant['name'])
				make_osm_line("ADDRESS", restaurant['original_address'])
				make_osm_line("CREATED", restaurant['date_created'])
				make_osm_line("FIRST_INSPECTION", restaurant['date_first_inspection'])
				make_osm_line("LAST_INSPECTION", restaurant['date_last_inspection'])

				if restaurant['name'] != restaurant['original_name']:
					make_osm_line("ORIGINAL_NAME", restaurant['original_name'])

				if (latitude == 0.0) and (longitude ==0.0):  # Tag for geocoding using geocode2osm
					make_osm_line ("GEOCODE", "yes")

				# Find municipality and county from looking up postal code translation

				if restaurant['postcode'] in postcode_districts:
					make_osm_line("MUNICIPALITY", postcode_districts[ restaurant['postcode'] ]['municipality_name'])
					make_osm_line("COUNTY", county_names[ postcode_districts[ restaurant['postcode'] ]['municipality_ref'][0:2] ])
				elif restaurant['postcode']:
					message ("Postcode not found: %s\n" % restaurant['postcode'])

				# Output previous geocode results, if any

				if restaurant['ref'] in old_restaurants:
					if "geocode_method" in old_restaurants[ restaurant['ref'] ]:
						make_osm_line("GEOMETHOD", old_restaurants[ restaurant['ref'] ]['geocode_method'])
					if "geocode_result" in old_restaurants[ restaurant['ref'] ]:
						make_osm_line("GEORESULT", old_restaurants[ restaurant['ref'] ]['geocode_result'])
				elif geocode_address and result:
					make_osm_line("GEOMETHOD", "Matrikkel/address -> Vegadresse")  # Same coding as geocode2osm.py
					make_osm_line("GEORESULT", "house")

				# Done with OSM store node

				file.write ('  </node>\n')

				if geocode_address and not result:
					message ("NOT FOUND: %s --> %s" % (restaurant['name'], restaurant['original_address']))
					if restaurant['address'] != restaurant['original_address']:
						message (" (%s)\n" % restaurant['address'])
					else:
						message ("\n")

		# Wrap up

		file.write ('</osm>\n')
		file.close()

		message ("\nSuccessfully geocoded %i restaurants + %i previously geocoded\n" % (count_new, count_old))
		message ("Written %i restaurants to file '%s'\n" % (count_output, filename))
		if count_new + count_old < count_output:
			message ("You may geocode the remaining %i restaurants with 'github.com/osmno/geocode2osm'\n" % (count_output - count_new - count_old))
		message ("\nLatest restaurant: %s\n" % latest_restaurant)
		message ("Latest inspection: %s\n" % latest_inspection)
		message ("First inspection:  %s\n\n" % first_inspection)

	elif unique_restaurants > max_restaurants:
		message ("Too many restaurants, please reduce scope of search\n")
	else:
		message ("No output file produced\n")

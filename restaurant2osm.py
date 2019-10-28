#!/usr/bin/env python2
# -*- coding: utf8

"""
restaurant2osm
Extracts restaurants from Mattilsynet inspections and produces OSM file for import/update
Usage: restaurant2osm [filter] [first inspection date]
Example filters: "query=Egon", "poststed=Oslo", "postnr=4885", "kommune=Bergen" (combine filters with &, use "")
The program produces restaurants which have their first inspection date on or after the given optional parameter
Writes output file to "restaurants.osm"
Reads postal/municipality codes from Posten and counties from Kartverket
"""

import json
import cgi
import sys
import time
import csv
import urllib
import urllib2
import re


version = "0.4.0"

header = { "User-Agent": "osm-no/restaurant2osm" }

debug = True

max_restaurants = 100000

transform_name = {
	'Airport': 'airport',
	'Alle': u'allé',
	'alle': u'allé',
	'AMFI': u'Amfi',
	'Bakeri': 'bakeri',
	'Brygge': 'brygge',
	u'Cafè': u'Café',
	u'cafè': u'café',
	u'Caffe': u'café',
	'Kafè' : 'kafé',
	'Gate': 'gate',
	u'Gård': u'gård',
	'Hagesenter': 'hagesenter',
	'Hotel': 'hotel',
	'Hotell': 'hotell',
	'Hos': 'hos',
	'I': 'i',
	'isushi': 'iSushi',
	'Lufthavn': 'lufthavn',
	'Mc Donald': "McDonald's",
	'McDonald': "McDonald's",
	'McDonalds': "McDonald's",
	u'McDonald´s': "McDonald's",
	u'McDonald`s': "McDonald's",
	'Og': 'og',
	'Plass': 'plass',
	u'På': u'på',
	'Senter': 'senter',
	'Sentrum': 'sentrum',
	'Stasjon': 'stasjon',
	'Storsenter': 'storsenter',
	'Torg': 'torg',
	'Torv': 'torv',
	# TODO takeaway, take-away, take
	'Veg': 'veg',
	'Vei': 'vei',
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
	u'è': u'é'
}

amenities = {
	'kafe': 'cafe',
	'cafe': 'cafe',
	u'kafé': 'cafe',
	u'café': 'cafe',
	'kaffe': 'cafe',
	'coffee': 'cafe',
	'espresso': 'cafe',
	'baker': 'bakery',
	u'brød': 'bakery',
	'kafeteria': 'cafe',
	'konditori': 'cafe',
	'conditori': 'cafe',
	'kiosk': 'cafe',
	'iskrembar': 'cafe',
	'juice': 'cafe',
	'hotel': '', #TODO
	'Starbucks': 'cafe',
	u'Jordbærpikene': 'cafe',
	'burger': 'fast_food',
	'kebab': 'fast_food',
	'Subway': 'fast_food',
	u'gatekjøkken': 'fast_food',
	'McDonald': 'fast_food',
	'Mc Donald': 'fast_food',
	'Burger King': 'fast_food'
}



def make_osm_line(key,value):

	"""Produce a tag for OSM file"""

	global file

	if value:
		encoded_value = cgi.escape(value.encode('utf-8'),True)
		file.write ('    <tag k="' + key + '" v="' + encoded_value + '" />\n')


def message (line):

	"""Output message"""

	sys.stdout.write (line)
	sys.stdout.flush()


def try_urlopen (url):

	"""Open file/api, try up to 5 times, each time with double sleep time"""

	tries = 0
	while tries < 5:
		try:
			return urllib2.urlopen(url)

		except urllib2.HTTPError, e:
			if e.code in [429, 503, 504]:  # "Too many requests", "Service unavailable" or "Gateway timed out"
				if tries  == 0:
					message ("\n") 
				message ("\r\tRetry %i in %ss... " % (tries + 1, 5 * (2**tries)))
				time.sleep(5 * (2**tries))
				tries += 1
			else:
				message ("\n\nHTTP error %i: %s\n" % (e.code, e.reason))
				message ("%s\n" % url.get_full_url())
				sys.exit()

		except urllib2.URLError, e:  # Mostly "Connection reset by peer"
			if tries  == 0:
				message ("\n") 
			message ("\r\tRetry %i in %ss... " % (tries + 1, 5 * (2**tries)))
			time.sleep(5 * (2**tries))
			tries += 1
	
	message ("\n\nError: %s\n" % e.reason)
	message ("%s\n\n" % url.get_full_url())
	sys.exit()


def get_address(street, house_number, postal_code, city):

	"""Concatenate address line"""

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


def geocode (street, house_number, house_letter, city):
	"""Geocoding with Kartverket Matrikkel/Vegnavn REST service"""

#	time.sleep(1)

	if house_number:

		if street[-1] == "-":  # Avoid Kartverket bug
			street = street[0: len(street) - 1]
		if ":" in street:
			street = street.replace(":", " ").replace("  ", " ")

		if house_letter:
			url = "https://ws.geonorge.no/adresser/v1/sok?sok=%s&nummer=%s&bokstav=%s&poststed=%s&treffPerSide=10" %\
					 (urllib.quote(street.encode('utf-8')), house_number, house_letter, urllib.quote(city.encode('utf-8')))
		else:
			url = "https://ws.geonorge.no/adresser/v1/sok?sok=%s&nummer=%s&poststed=%s&treffPerSide=10" %\
					 (urllib.quote(street.encode('utf-8')), house_number, urllib.quote(city.encode('utf-8')))

		request = urllib2.Request(url)
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


if __name__ == '__main__':

	"""Main program"""

	message ("\nRestaurants from Mattilsynet's inspections\n")
	
	if len(sys.argv) > 1:
		input_query = sys.argv[1].decode("utf-8")
	else:
		input_query = ""

	if len(sys.argv) > 2:
		input_date = sys.argv[2]
	else:
		input_date = "1900-01-01"

	# Read county names

	filename = "https://register.geonorge.no/api/sosi-kodelister/fylkesnummer.json?"
	file = urllib2.urlopen(filename)
	county_data = json.load(file)
	file.close()

	county_names = {}
	for county in county_data['containeditems']:
		if county['status'] == "Gyldig":
			county_names[county['codevalue']] = county['label'].strip()

	# Read postal codes and municipality codes from Posten (updated daily)

	file = urllib2.urlopen('https://www.bring.no/postnummerregister-ansi.txt')
	postal_codes = csv.DictReader(file, fieldnames=['zip','post_city','municipality_ref','municipality_name','type'], delimiter="\t")
	postcode_districts = {}
	for row in postal_codes:
		postcode_districts[ row['zip'] ] = {
			'city': row['post_city'].decode("windows-1252").strip().title(),
			'municipality_ref': row['municipality_ref'],
			'municipality_name': row['municipality_name'].decode("windows-1252").strip().title()
		}
	file.close()

	# If municipality is a filter then get all post codes for municipality

	municipality_target = ""
	query_split = input_query.split("&")
	for query_part in query_split:
		if query_part[0:8] == "kommune=":
			municipality_target = query_part[8:]
			if municipality_target == "Oslo":  # More efficient to get Oslo through one post district query
				input_query = input_query.replace("kommune=Oslo", "poststed=Oslo")
				municipality_target = ""

	target_list = []
	if municipality_target:
		for postcode in postcode_districts:
			if postcode_districts[postcode]['municipality_name'] == municipality_target.title():
				target_list.append(postcode)

	if not(target_list):
		if municipality_target:
			message ("No postcodes found for %s municipality\n" % municipality_target)
			sys.exit()
		else:
			target_list = ['9999']  # Dummy entry to get one iteration

	# Get info about latest update

	url = "https://hotell.difi.no/api/json/mattilsynet/smilefjes/tilsyn?"
	request = urllib2.Request(url, headers=header)
	file = urllib2.urlopen(request)
	inspection_data = json.load(file)
	file.close()

	url += "page=%i" % inspection_data['pages']
	request = urllib2.Request(url, headers=header)
	file = urllib2.urlopen(request)
	inspection_data = json.load(file)
	file.close()

	inspection = inspection_data['entries'][-1]
	latest_inspection = "%s-%s-%s" % (inspection['dato'][4:8], inspection['dato'][2:4], inspection['dato'][0:2])
	message ("Inspections in database:  %i\n" % inspection_data['posts'])
#	message ("Latest entry in database: %s (%s, %s)\n\n" % (latest_inspection, inspection['navn'], inspection['poststed'].title()))

	# Read all data into memory	

	message ("Loading data... ")

	restaurants = []
	total_restaurants = 0
	unique_restaurants = 0

	for target in target_list:  # Iterate all post codes for municipality, if filter

		query = input_query
		if municipality_target:
			query = query.replace("kommune=" + municipality_target, "postnr=" + target)

		page = 0
		total_pages = 9999

		while page < total_pages:  # Iterate all pages with results of query

			page += 1
			url = "https://hotell.difi.no/api/json/mattilsynet/smilefjes/tilsyn?%s&page=%i" % \
					(urllib.quote(query.encode("utf-8"), safe="&="), page)
			request = urllib2.Request(url, headers=header)
			file = urllib2.urlopen(request)
			inspection_data = json.load(file)
			file.close()

			for inspection in inspection_data['entries']:  # Iterate all inspections on result page

				entry = {}

				# Fix name

				name = inspection['navn']
				if name == name.upper():
					name = name.title()
				name_split = name.split()
				for word in name_split[1:]:
					for word_from, word_to in transform_name.iteritems():
						if word == word_from:
							name = name.replace(word_from, word_to)

				date_inspection = "%s-%s-%s" % (inspection['dato'][4:8], inspection['dato'][2:4], inspection['dato'][0:2])

				entry['name'] = name.replace("  "," ").strip()
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

				elif name.find(" M/S") < 0:
					restaurants.append(entry)
					unique_restaurants += 1

			total_pages = inspection_data['pages']

		total_restaurants += inspection_data['posts']

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

	count = 0

	if (unique_restaurants > 0) and (unique_restaurants < max_restaurants):

		# Produce OSM file header

		message ("Geocoding and generating output file...\n")

		filename = "restaurants.osm"
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

				result = geocode (restaurant['street'], restaurant['house_number'], restaurant['house_letter'], restaurant['city'])

				if result:
					latitude = result[0]
					longitude = result[1]
					count += 1

				else:
					# Attempt new geocoding after fixing street name

					street = restaurant['street'] + " "
					old_street = street
					for word_from, word_to in transform_address.iteritems():
						street = street.replace(word_from, word_to)
						street = street.replace(word_from.upper(), word_to.upper())

					if street != old_street:
						result = geocode (street, restaurant['house_number'], restaurant['house_letter'], restaurant['city'])
						if result:
							latitude = result[0]
							longitude = result[1]
							count += 1

				node_id -= 1

				file.write ('  <node id="%i" lat="%f" lon="%f">\n' % (node_id, latitude, longitude))

				# Decide amenity type

				amenity = "restaurant"
				for keyword, amenity_value in amenities.iteritems():
					if restaurant['name'].lower().find(keyword.lower()) >= 0:
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
				else:
					message ("Postcode not found: %s\n" % restaurant['postcode'])

				# Done with OSM store node

				file.write ('  </node>\n')

				if not(result):
					message ("Address not geocoded: %s --> %s" % (restaurant['name'], restaurant['original_address']))
					if restaurant['address'] != restaurant['original_address']:
						message (" (%s)\n" % restaurant['address'])
					else:
						message ("\n")

		# Wrap up

		file.write ('</osm>\n')
		file.close()

		message ("\nSuccessfully geocoded %i of %i restaurants\n" % (count, unique_restaurants))
		message ("Written %i restaurants to file '%s'\n" % (unique_restaurants, filename))
		if count < unique_restaurants:
			message ("You may geocode the remaining %i restaurants with 'github.com/osmno/geocode2osm'\n" % (unique_restaurants - count))
		message ("\nLatest restaurant: %s\n" % latest_restaurant)
		message ("Latest inspection: %s\n" % latest_inspection)
		message ("First inspection:  %s\n\n" % first_inspection)

	elif unique_restaurants > max_restaurants:
		message ("Too many restaurants, please reduce scope of search\n")
	else:
		message ("No output file produced\n")

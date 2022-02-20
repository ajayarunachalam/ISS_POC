from datetime import datetime, timedelta
import re
import time
import csv
import argparse
import threading
import warnings

import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


warnings.filterwarnings('ignore')
lock = threading.Lock()
km_per_hr_to_miles_per_sec_factor = 0.6213711922 / 3600


def interval_regex_type(value):
	pattern = re.compile(r'^(?P<number>[1-9]\d*)(?P<unit>[smh])$')
	match = pattern.match(value)
	if match is None:
		raise argparse.ArgumentTypeError('Incorrect interval syntax!')
	return match.groupdict()


parser = argparse.ArgumentParser('Fetch ISS location data')
parser.add_argument(
	'-i', '--interval', required=True, type=interval_regex_type,
	help='Time interval for each API call'
)
parser.add_argument(
	'-o', '--output-file', required=True, type=str,
	help='Path to the output CSV file'
)
parser.add_argument(
	'-p', '--preprocess', action='store_true',
	help='Pre-process the raw data'
)


def get_interval_in_seconds(interval):
	interval_in_secs = int(interval['number'])
	if interval['unit'] == 'm':
		interval_in_secs *= 60
	elif interval['unit'] == 'h':
		interval_in_secs *= 3600
	return interval_in_secs


def get_api_response(url, **kwargs):
	response = requests.get(url, **kwargs)
	return response.json()


def write_row_to_file(row_dict, filename, header):
	row = (row_dict[key] for key in header)

	write_header = False
	with open(filename, 'a+', newline='') as csvfile:
		# Reading and analyzing CSV
		csvfile.seek(0)
		reader = csv.reader(csvfile)
		try: write_header = next(reader) != header
		except StopIteration: write_header = True
		
		# Writing row
		writer = csv.writer(csvfile)
		if write_header:
			csvfile.seek(0)
			csvfile.truncate()
			writer.writerow(header)
			print(f'Written header to {filename}')
		csvfile.seek(0, 2)
		writer.writerow(row)
		print(f'Written row to {filename}')


def pre_process(latitude, longitude):
	geolocator = Nominatim(user_agent='WhereIsTheISS')
	reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1, return_value_on_exception=None)
	location = reverse((latitude, longitude))

	if location is None:
		return {}
	location_dict = location.raw
	location_dict.update(location_dict['address'])
	return location_dict


def call_api_and_store_result_in_file(url, filename, preprocess):
	header = [
		'time', 'name', 'id', 'latitude', 'longitude', 'altitude', 'velocity', 'visibility',
		'footprint', 'timestamp', 'daynum', 'solar_lat', 'solar_lon', 'units'
	]

	iss_json = get_api_response(url, verify=False)
	iss_json['time'] = datetime.now()
	if preprocess:
		location_header = ['place_id', 'display_name', 'address', 'boundingbox']
		location_info = pre_process(iss_json['latitude'], iss_json['longitude'])
		iss_json.update({key: location_info.get(key) for key in location_header})
		header.extend(location_header)

		iss_json['velocity'] *= km_per_hr_to_miles_per_sec_factor
		iss_json['units'] = 'miles'
		iss_json['timestamp'] = datetime.utcfromtimestamp(iss_json['timestamp'])
	with lock:
		write_row_to_file(iss_json, filename, header)


def request_until_stopped(interval_in_secs, filename, preprocess):
	iss_api_endpoint_url = 'https://api.wheretheiss.at/v1/satellites/25544'

	# Request until stopped by user
	try:
		delta = timedelta(seconds=interval_in_secs)
		next_call = datetime.now() + delta

		while True:
			threading.Thread(target=call_api_and_store_result_in_file, args=(iss_api_endpoint_url, filename, preprocess)).start()
			time_to_sleep = (next_call - datetime.now()).microseconds * 1e-6
			time.sleep(time_to_sleep)
			next_call += delta
	except KeyboardInterrupt:
		print('Process done!')


if __name__ == '__main__':
	args = parser.parse_args()

	# Determine time interval
	interval_in_secs = get_interval_in_seconds(args.interval)

	# Request
	request_until_stopped(interval_in_secs, args.output_file, args.preprocess)

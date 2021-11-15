import sys
import re
import requests
import json
from progress.bar import Bar
from ratelimit import limits, sleep_and_retry

try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
except Exception:
    redis_client = None

GEO_BATCH_SIZE = 100
ONE_MINUTE = 60


def parse_ips(file_path: str) -> list[str]:
    with open(file_path) as file:
        raw_text = file.read()
        ips = re.findall("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", raw_text)
        return ips


@sleep_and_retry
@limits(calls=15, period=ONE_MINUTE)
def fetch_geo_batch(ips: list[str]):
    url = "http://ip-api.com/batch"
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}
    batch_response = requests.post(
        url, data=json.dumps(ips), headers=headers)
    batch_result = batch_response.json()
    return batch_result


def geo_lookup(ips_data: dict[str, dict]):
    ips_data_copy = ips_data.copy()
    ips = ips_data_copy.keys()
    if redis_client:
        unknown_ips = []
        for ip in ips:
            redis_key = "{}_geo_data".format(ip)
            if redis_client.exists(redis_key):
                result = json.loads(redis_client.get(redis_key))
                ips_data_copy[ip]["geo_data"] = result
            else:
                unknown_ips.append(ip)
    else:
        unknown_ips = ips
    bar = Bar('Fetching Geo Data', max=len(unknown_ips))
    for i in range(0, len(unknown_ips), GEO_BATCH_SIZE):
        ips = unknown_ips[i:i+GEO_BATCH_SIZE]
        batch_result = fetch_geo_batch(ips)
        for result in batch_result:
            ip = result["query"]
            ips_data_copy[ip]["geo_data"] = result
            if redis_client:
                redis_key = "{}_geo_data".format(ip)
                redis_client.set(redis_key, json.dumps(result))
        bar.next(n=100)
    return ips_data_copy


def rdap_lookup(ips_data: dict[str, dict]):
    bar = Bar('Processing RDAP Lookup', max=len(ips_data))
    ips_data_copy = ips_data.copy()
    for ip in ips_data_copy.keys():
        url = "https://rdap.org/ip/{}".format(ip)
        if redis_client:
            redis_key = "{}_rdap_data".format(ip)
            if redis_client.exists(redis_key):
                result = json.loads(redis_client.get(redis_key))
            else:
                result = requests.get(url).json()
                redis_client.set(redis_key, json.dumps(result))
        else:
            result = requests.get(url).json()
        ips_data_copy[ip]["rdap_data"] = result
        bar.next()
    return ips_data_copy


if __name__ == "__main__":
    file_path = sys.argv[1]
    ips = parse_ips(file_path)
    ips_data = {ip: {} for ip in ips}
    ips_data = geo_lookup(ips_data)
    ips_data = rdap_lookup(ips_data)
    print(ips_data)

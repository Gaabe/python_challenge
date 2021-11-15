# Overview
The required dependencies are listed in the `requirements.txt` file, and can be installed using `pip`
```
pip install -r requirements.txt
```

To run the program, you need to pass the path of the file containing the ips as an argument, as an example:
```
python3 geo_lookup.py list_of_ips.txt
```

For better performance over multiple runs, this script tries to make use of redis if available, and cache all the fetched data.
You can check instructions on how to set up redis at https://redis.io/topics/quickstart

# Warnings
RDAP look ups are very slow, because most of the available apis have severe rate limits, please have in mind that looking up a large number of ips will take a long time.

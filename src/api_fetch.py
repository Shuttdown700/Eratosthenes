#!/usr/bin/env python

class API(object):
    def __init__(self):
        pass
    def __str__(self):
        pass
    
    
import requests

url = "https://api.themoviedb.org/3/search/movie?query=fall%20guy&include_adult=false&language=en-US&page=1"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxMDk1M2ExY2M3YzI5MWNkYmVkZDQ4OTBjOWYwMjAxNyIsIm5iZiI6MTcyNTEyMDQ5My4xNTMzNDEsInN1YiI6IjY2ZDMzODk1OGVmZWZkYzU5NzZhNmYwZiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.xTmJSm6PYOXR__1rAO1dzN7WpIFCnvBBWJ1GoQdE_1U"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    # Parse the JSON response using the .json() method
    data = response.json()


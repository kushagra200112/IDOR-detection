import requests
def get_headers(url):
    response=requests.get(url)

    print(response.headers)
    return (response.headers)

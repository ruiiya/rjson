import urllib.request

functions = {}

def fetch_len(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        data = r.read()
        return len(data)

functions['fetch_len'] = fetch_len

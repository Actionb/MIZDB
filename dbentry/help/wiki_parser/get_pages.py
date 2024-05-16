from pathlib import Path

import requests


def get_all_pages():
    """Use the mediawiki api to get the names of all pages of MIZDB wiki."""
    # https://www.mediawiki.org/wiki/API:Allpages
    url = "http://serv01/mediawiki/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "aplimit": 500,
    }
    session = requests.Session()
    response = session.get(url=url, params=params)
    data = response.json()
    return data["query"]["allpages"]


def write_pages(pages):
    """
    Parse the content of each MIZDB wiki page and write the HTML content to a
    local file.
    """
    # https://www.mediawiki.org/w/api.php?action=help&modules=parse
    session = requests.Session()
    url = "http://serv01/mediawiki/api.php"
    base_params = {"action": "parse", "formatversion": 2, "format": "json"}
    path = Path(__file__).parent / "in"
    for page in pages:
        params = {"page": page["title"], **base_params}
        try:
            response = session.get(url=url, params=params)
        except Exception as e:  # noqa
            print(f"Could not get a response with {params=}\n{e}")
            continue
        if not response.ok:
            print(f"Request failed: {response.status_code}\n{response.url=}")
            continue
        try:
            data = response.json()
        except Exception as e:  # noqa
            print(f"Could not create json for {page['title']}\n{response.url=}\n{e}")
            continue
        text = data["parse"]["text"]
        with open(path / f"{page['title'].lower()}.html", "w") as f:
            f.write(text)


if __name__ == '__main__':
    write_pages(get_all_pages())

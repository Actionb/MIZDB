import os
from pathlib import Path

import django
import requests
from bs4 import BeautifulSoup  # noqa
from django.urls import resolve, Resolver404

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MIZDB.settings.development")
django.setup()


def find_dead_links(base_url="http://127.0.0.1:8000"):
    """
    Make requests against all help links found on all help page to see if any
    link is broken.
    """
    session = requests.session()
    response = session.get(base_url)
    if response.status_code != requests.codes.ok:
        print(f"Could not get a response from {base_url=}.")
        print("\nIs the dev server running?")
        return

    template_dir = Path(__file__).parent / "templates" / "help"
    for template in template_dir.iterdir():
        with open(template, "r") as f:
            try:
                soup = BeautifulSoup(f.read(), "html.parser")
            except:  # noqa
                print(f"Could not make soup for {template.name}")
            for link in soup.find_all("a"):
                url = link.get("href")
                if "mediawiki" in url:
                    print(f"{template.name=} contains link to mediawiki page")
                if not url.startswith("/help") or "Datei" in url:
                    continue
                if not url.endswith("/"):
                    url = f"{url}/"
                try:
                    resolve(url)
                except Resolver404:
                    print(f"Could not resolve {url=} from {template.name=}")
                response = session.get(base_url + url)
                if response.status_code != 200:
                    print(f"Got {response.status_code=} on {url=}")


if __name__ == '__main__':
    find_dead_links()

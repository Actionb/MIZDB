import shutil
from pathlib import Path

from bs4 import BeautifulSoup

project_root = Path(__file__).parent.parent.parent
site_root = project_root / "dbentry" / "site"
static_root = site_root / "static"


def _replace_urls(content):
    requires_load_static = False

    def is_link_or_img(node):
        return node.name in ("a", "img")

    for elem in content.find_all(is_link_or_img):
        if elem.name == "img":
            key = "src"
        else:
            key = "href"
        url = elem.attrs[key]
        if url.startswith("img/"):
            elem.attrs[key] = "{% static " + f"'{url}'" + " %}"
            requires_load_static = True  # need to load the static tag
        elif "/" not in url and url.endswith(".html"):
            elem.attrs[key] = "{% url 'help' page_name=" + f"'{url.replace('.html', '')}'" + "%}"

    return requires_load_static


def copy_glightbox_assets(config):
    assets_dirs = Path(config["site_dir"]) / "assets"
    dst_dir = static_root / "help"
    if not assets_dirs.exists():
        return
    dst_dir.joinpath("js").mkdir(exist_ok=True)
    dst_dir.joinpath("css").mkdir(exist_ok=True)
    try:
        shutil.copy(assets_dirs / "javascripts" / "glightbox.min.js", dst_dir / "js" / "glightbox.min.js")
        shutil.copy(assets_dirs / "stylesheets" / "glightbox.min.css", dst_dir / "css" / "glightbox.min.css")
    except Exception as e:
        print("Failed to copy glightbox:", e)


def parse_pages(config):
    if config.get("templates_out_dir", None):
        out_dir = Path(config.get("templates_out_dir", None))
    else:
        out_dir = project_root / "dbentry" / "site" / "templates" / "help"
    out_dir.mkdir(exist_ok=True)
    exclude = ("main.html", "404.html")
    for page in Path(config["site_dir"]).iterdir():
        if page.is_file() and page.suffix == ".html" and not page.name in exclude:
            with open(page, "r") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            content = soup.find(id="help_content")
            if not content:
                continue
            requires_static = _replace_urls(content)
            with open(out_dir / page.name, "w") as f:
                f.write('{% extends "help/base.html" %}')
                if requires_static:
                    f.write("{% load static %}")
                f.write("{% block content %}")
                f.write(str(content))
                f.write("{% endblock content %}")


def on_post_build(config):
    parse_pages(config)
    copy_glightbox_assets(config)

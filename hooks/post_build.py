import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

# project_root/docs/docs/hooks
project_root = Path(__file__).parents[3]
site_root = project_root / "dbentry" / "site"
static_root = site_root / "static"


def _replace_urls(content):
    pattern = re.compile(r"(.*).html(#.*)?")
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
        elif "/" not in url and "html" in url:
            match = pattern.search(url)
            if not match:
                continue
            page_name = match.group(1)  # TODO: need to use unquote?
            fragment = ""
            if match.group(2) and len(match.group(2)) > 1:
                group = match.group(2)
                # Use lower case for fragment:
                # Foo#Index -> Foo#index
                fragment = group[0] + group[1].lower() + group[2:]
            elem.attrs[key] = "{% url 'help' page_name=" + f"'{page_name}'" + "%}" + fragment

    return requires_load_static


def copy_glightbox_assets(config):
    assets_dirs = Path(config["site_dir"]) / "assets"
    dst_dir = static_root / "help"
    if not assets_dirs.exists():
        return
    dst_dir.joinpath("js").mkdir(exist_ok=True, parents=True)
    dst_dir.joinpath("css").mkdir(exist_ok=True, parents=True)
    try:
        shutil.copy(assets_dirs / "javascripts" / "glightbox.min.js", dst_dir / "js" / "glightbox.min.js")
        shutil.copy(assets_dirs / "stylesheets" / "glightbox.min.css", dst_dir / "css" / "glightbox.min.css")
    except Exception as e:
        print("Failed to copy glightbox:", e)


def copy_css(config):
    src_dir = Path(config["site_dir"]) / "css"
    dst_dir = static_root / "help" / "css"
    if not src_dir.exists():
        return
    dst_dir.mkdir(exist_ok=True, parents=True)
    shutil.copy(src_dir / "base.css", dst_dir / "base.css")
    shutil.copy(src_dir / "admonitions.css", dst_dir / "admonitions.css")
    shutil.copy(src_dir / "toc_scroll.css", dst_dir / "toc_scroll.css")


def copy_js(config):
    src_dir = Path(config["site_dir"]) / "js"
    dst_dir = static_root / "help" / "js"
    if not src_dir.exists():
        return
    dst_dir.mkdir(exist_ok=True, parents=True)
    shutil.copy(src_dir / "style.js", dst_dir / "style.js")


def parse_pages(config):
    if config.get("templates_out_dir", None):
        out_dir = Path(config.get("templates_out_dir", None))
    else:
        out_dir = project_root / "dbentry" / "site" / "templates" / "help"
    out_dir.mkdir(exist_ok=True, parents=True)
    exclude = ("main.html", "404.html")
    for page in Path(config["site_dir"]).iterdir():
        if page.is_file() and page.suffix == ".html" and page.name not in exclude:
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
    copy_css(config)
    copy_js(config)

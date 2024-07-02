import shutil
from pathlib import Path

from bs4 import BeautifulSoup

project_root = Path(__file__).parent.parent.parent
site_root = project_root / "dbentry" / "site"
static_root = site_root / "static"


def image_static_tag(url):
    """
    Wrap the image URL in a django static tag.

    Note, mkdocs images are served directly from the 'docs' directory:
    STATICFILES_DIRS = [
        BASE_DIR / "docs",  # include static files for help pages, such as images
    ]
    """
    return "{% static " + f"'{url}'" + " %}"


def url_tag(url):
    """Return a django 'url' tag that reverses the given URL to the corresponding HelpView."""
    return "{% url 'help' page_name=" + f"'{url.replace('.html', '')}'" + "%}"

def _replace_urls(content):
    requires_static = False
    for link in content.find_all("a"):
        try:
            href = link.attrs["href"]
        except (KeyError, AttributeError):
            continue
        if href.startswith("img/"):
            link.attrs["href"] = image_static_tag(href)
            requires_static = True
        elif "/" not in href and href.endswith(".html"):
            link.attrs["href"] = "{% url 'help' page_name=" + f"'{href.replace('.html', '')}'" + "%}"
    for img in content.find_all("img"):
        if img.attrs["src"].startswith("img/"):
            try:
                src = img.attrs["src"]
            except (KeyError, AttributeError):
                continue
            img.attrs["src"] = image_static_tag(src)
            requires_static = True

    return requires_static


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
    for page in Path(config["site_dir"]).iterdir():
        if page.is_file() and page.suffix == ".html":
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

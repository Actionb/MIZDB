"""Parse the content of a WIKI page and create a stripped-down HTML version of it."""
import re
import sys
import textwrap
from functools import partial, cached_property
from pathlib import Path

from bs4 import BeautifulSoup, Tag


class WikiParser:

    def __init__(self, title, html):
        self.title = title
        self.html = html
        self.elements = []

    @cached_property
    def soup(self):
        return BeautifulSoup(self.html, "html.parser")

    def parse(self):
        find = partial(self.find, self.soup)
        heading = self.soup.new_tag("h1", attrs={"class": "border-bottom"})
        heading.string = self.title
        self.add(heading)
        self.add(find("p"))
        toc = find(id="toc")
        self.add(toc)
        if self.elements:
            for tag in self.elements[-1].find_next_siblings(lambda t: t.name != "div"):
                self.clean_tag(tag)
                self.add(tag)
        return self.elements

    def add(self, tag):
        if tag is not None:
            self.elements.append(tag)

    def find(self, soup, *args, **kwargs):
        tag = soup.find(*args, **kwargs)
        self.clean_tag(tag)
        return tag

    def clean_tag(self, tag: Tag):
        if tag is None:
            return
        self._strip_class(tag)
        self._add_class(tag)
        self._strip_edit_link_sections(tag)
        self._update_links(tag)
        self._strip_self_links(tag)
        self._strip_image_links(tag)
        self._strip_broken_links(tag)

    def _strip_class(self, tag: Tag):
        tag.attrs.pop("class", None)

    def _add_class(self, tag: Tag):
        if tag.name == "table":
            tag["class"] = ["table"]
        elif tag.name in ("h1", "h2", "h3"):
            tag["class"] = ["border-bottom"]
        elif tag.name == "h6":
            tag["class"] = ["fw-bold"]

    def _strip_edit_link_sections(self, tag: Tag):
        try:
            tag.find("span", attrs={"class": "mw-editsection"}).decompose()
        except AttributeError:
            pass

    def _update_links(self, tag: Tag):
        wiki_prefix = "/wiki"
        for a in tag.find_all(href=re.compile(rf"^{wiki_prefix}")):
            a["href"] = a["href"].replace(wiki_prefix, "/help")

    def _strip_self_links(self, tag: Tag):
        for a in tag.find_all(class_="selflink"):
            a.replace_with(a.string)

    def _strip_image_links(self, tag: Tag):
        if link := tag.find("a", class_="image"):
            # This tag contains a wiki image. Ignore:
            link.decompose()

    def _strip_broken_links(self, tag: Tag):
        # Remove links to pages that do not exist
        for link in tag.find_all("a"):
            if "Seite nicht vorhanden" in link.get("title", ""):
                link.replace_with(link.string)

    def as_html(self):
        # TODO: add proper <head>
        template = textwrap.dedent(
            """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title></title>
        <meta name="description" content="">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
        <link id="default_theme" href="/static/mizdb/css/mizdb_theme.css" rel="stylesheet">
    </head>
    <body class="container">
        %s
    </body>
</html>
            """
        )
        return template % f"\n{' ' * 8}".join(str(t) for t in self.elements if t is not None)


def parse_main_page():
    with open(Path(__file__).parent / "in" / "hauptseite.html", "r") as f:
        parser = WikiParser("Hauptseite", f.read())
        for tag in parser.soup.contents:
            parser.clean_tag(tag)
            parser.add(tag)
    with open(Path(__file__).parent / "out" / "hauptseite.html", "w") as out:
        out.write(parser.as_html())


def parse_wiki_pages():
    out_path = Path(__file__).parent / "out"
    in_path = Path(__file__).parent / "in"
    for html_file in in_path.iterdir():
        if html_file.suffix == ".html" and html_file.stem != "hauptseite":
            with open(html_file, "r") as f:
                parser = WikiParser(html_file.stem.title(), f.read())
            parser.parse()
            with open(out_path / html_file.name, "w") as out:
                out.write(parser.as_html())
    parse_main_page()


def create_templates():
    out_path = Path(__file__).parent / "out"
    templates_path = Path(__file__).parent.parent / "templates" / "help"
    for html_file in out_path.iterdir():
        with open(html_file, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        with open(templates_path / html_file.name.replace(" ", "_"), "w") as f:
            f.write("""{% extends "help/help_base.html" %}\n\n{% block content %}""")
            for tag in soup.body.contents:
                f.write(str(tag))
            f.write("{% endblock content %}")


if __name__ == '__main__':
    cmd = sys.argv[-1]
    if cmd == "wiki":
        parse_wiki_pages()
    elif cmd == "templates":
        create_templates()
    elif cmd == "all":
        parse_wiki_pages()
        create_templates()

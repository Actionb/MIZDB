"""Parse the content of a WIKI page and create a stripped-down HTML version of it."""

import re
import sys
import textwrap
from functools import cached_property
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
        self._make_tables()
        self._add_heading()

        if first_paragraph := self.soup.find("p"):
            self.clean_tag(first_paragraph)
            self.add(first_paragraph)
            for tag in first_paragraph.find_next_siblings():
                if isinstance(tag, Tag):
                    if tag.id == "toc":
                        self._add_toc()
                    elif tag.name == "div":
                        continue
                    else:
                        self.clean_tag(tag)
                        self.add(tag)

        return self.elements

    def add(self, tag):
        def is_empty_p(t):
            return t.name == "p" and str(t) == "<p><br/>\n</p>"
        if tag is not None and not is_empty_p(tag):
            self.elements.append(tag)

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
        self._replace_felder_heading(tag)

    def _strip_class(self, tag: Tag):
        if tag.name != "table":
            tag.attrs.pop("class", None)

    def _add_class(self, tag: Tag):
        def is_beschreibung_paragraph(t):
            """
            Check whether the immediate previous siblings of the given p element
            are the headings for the 'Beschreibung' or 'Bemerkungen' fields.
            """
            for i, sibling in enumerate(t.previous_siblings):
                if i > 1:
                    # Only check up to the second previous sibling.
                    # (the first previous sibling could just be an empty text
                    # node)
                    return False
                if sibling.name == "h6" and sibling.span and sibling.span.get("id") in ("Beschreibung", "Bemerkungen"):
                    return True

        if tag.name in ("h1", "h2", "h3"):
            tag["class"] = ["border-bottom"]
        elif tag.name == "h6":
            tag["class"] = ["fw-bold"]
        elif tag.name == "dl":
            tag["class"] = ["ms-4"]
        elif tag.name == "p" and is_beschreibung_paragraph(tag):
            # Beschreibung & Bemerkungen fields
            tag["class"] = ["ms-4"]

    def _strip_edit_link_sections(self, tag: Tag):
        try:
            tag.find("span", attrs={"class": "mw-editsection"}).decompose()
        except AttributeError:
            pass

    def _update_links(self, tag: Tag):
        wiki_prefix = "/wiki"
        for a in tag.find_all(href=re.compile(rf"^{wiki_prefix}")):
            a["href"] = a["href"].replace(wiki_prefix, "/help")
            if not a["href"].endswith("/"):
                a["href"] += "/"

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

    def _replace_felder_heading(self, tag: Tag):
        if tag.name == "h2":
            tag.name = "h3"

    def _make_tables(self):
        for table in self.soup.find_all("table"):
            self._make_table(table)

    def _make_table(self, table):
        table["class"] = ["table", "table-bordered"]
        try:
            del table["style"]
        except:  # noqa
            pass

        # Move table header elements into thead from tbody
        if table.find("thead"):
            # probably already fine
            return
        thead = self.soup.new_tag("thead", attrs={"class": "text-center table-primary"})
        for row in table.tbody.find_all("tr"):
            if row.find("th"):
                thead.append(row.extract())
                # row.decompose()
        table.tbody.insert_before(thead)

        # Text align for table body:
        table.tbody["class"] = ["text-end"]

    def _parse_toc(self, toc):
        # Add a toggle button
        if toctitle := toc.find("div", class_="toctitle"):
            toggle_button = self.soup.new_tag(
                "button",
                attrs={"class": "btn btn-sm btn-link", "data-bs-toggle": "collapse", "data-bs-target": "#toc>ul"},
            )
            toggle_button.string = "[Verbergen/Anzeigen]"
            toctitle.append(toggle_button)
            toctitle["class"].append("d-flex")
            if heading := toctitle.find("h2"):
                heading.name = "h4"

        if ul := toc.find("ul"):
            ul["class"] = ["collapse", "list-unstyled"]

        toc.get("class", []).extend(["border bg-primary bg-opacity-10", "px-4", "py-2", "mb-3"])
        toc["style"] = "max-width: 500px;"

    def _add_toc(self):
        toc = self.soup.find(id="toc")
        if toc:
            self._parse_toc(toc)
            self.add(toc)

    def _add_heading(self):
        heading = self.soup.new_tag("h1", attrs={"class": "border-bottom"})
        heading.string = self.title
        self.add(heading)

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


if __name__ == "__main__":
    cmd = sys.argv[-1]
    if cmd == "wiki":
        parse_wiki_pages()
    elif cmd == "templates":
        create_templates()
    elif cmd == "all":
        parse_wiki_pages()
        create_templates()

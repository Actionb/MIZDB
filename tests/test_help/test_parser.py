import pathlib

import pytest
from bs4 import BeautifulSoup

from dbentry.help.wiki_parser.parser import WikiParser


class TestWikiParser:

    @pytest.fixture
    def html(self):
        return ""

    @pytest.fixture
    def file_html(self):
        path = pathlib.Path(__file__).parent / "wiki_html.html"
        with open(path, "r") as f:
            return f.read()

    @pytest.fixture
    def parser(self, html):
        return WikiParser("Test", html)

    @pytest.fixture
    def file_parser(self, file_html):
        return WikiParser("File Test", file_html)

    @pytest.fixture
    def make_tag(self):
        def inner(html):
            return BeautifulSoup(html, "html.parser").contents[0]

        return inner

    def test_parse(self, file_parser):
        elements = file_parser.parse()
        assert elements[0].name == "h1"
        assert elements[1].name == "p"

    def test_strip_class(self, parser, make_tag):
        html = """<p id="p1" class="foo">Foo</p>"""
        tag = make_tag(html)
        parser._strip_class(tag)
        assert str(tag) == """<p id="p1">Foo</p>"""

    def test_strip_edit_link_sections(self, parser, make_tag):
        html = """<div><span class="foo">Foo</span><span class="mw-editsection">Bar</span></div>"""
        tag = make_tag(html)
        parser._strip_edit_link_sections(tag)
        assert str(tag) == """<div><span class="foo">Foo</span></div>"""

    def test_update_links(self, parser, make_tag):
        html = """<p>Text <a href="#foo">foo</a> text <a href="/wiki/bar">bar</a>.</p>"""
        tag = make_tag(html)
        parser._update_links(tag)
        assert str(tag) == """<p>Text <a href="#foo">foo</a> text <a href="/help/bar">bar</a>.</p>"""

    def test_strip_self_links(self, parser, make_tag):
        html = """<dl><dt>Foo <a class="selflink">Bar</a> Baz</dt></dl>"""
        tag = make_tag(html)
        parser._strip_self_links(tag)
        assert str(tag) == """<dl><dt>Foo Bar Baz</dt></dl>"""

    def test_strip_image_links(self, parser, make_tag):
        html = """<p><a href="" class="image"><img></img></a></p>"""
        tag = make_tag(html)
        parser._strip_image_links(tag)
        assert str(tag) == "<p></p>"

    def test_add_class_beschreibung(self):
        html = """
        <h6 class="fw-bold"><span class="mw-headline" id="Beschreibung">Beschreibung</span></h6>
        <p>Ein Feld für weitere Angaben, welche in kein anderes der Felder passen.
        </p>
        """
        parser = WikiParser("Test", html.replace("\n", ""))
        parser.parse()
        assert "ms-4" in str(parser.soup.find("p").get("class", ""))

    def test_make_table(self, parser):
        html = """
        <table style="text-align:right;">
            <tbody>
                <tr>
                    <th>Heading 1</th>
                    <th>Heading 2</th>
                </tr>
                <tr>
                    <td>Value 1</td>
                    <td>Value 2</td>
                </tr>
            </tbody>
        </table>
        """
        parser = WikiParser("Test", html)
        table = parser.soup.table
        parser._make_tables()
        assert table["class"] == ["table", "table-bordered"]

        assert table.thead
        assert table.thead["class"] == ["text-center", "table-primary"]
        assert len(list(table.thead.find_all("tr"))) == 1
        assert len(list(table.thead.find_all("th"))) == 2

        assert table.tbody["class"] == ["text-end"]
        assert len(list(table.tbody.find_all("tr"))) == 1
        assert len(list(table.tbody.find_all("td"))) == 2

    def test_parse_toc(self, parser):
        html = """
        <div id="toc">
            <div class="toctitle">
                <h2>ToC</h2>
            </div<>
            <ul>
                <li>First Item</li>
                <li>
                    <ul><li>Second Item</li></ul>
                </li>
            </ul>
        </div>
        """
        parser = WikiParser("Test", html)
        toc = parser.soup.find(id="toc")
        parser._parse_toc(toc)

        toctitle = toc.find("div", class_="toctitle")
        assert toctitle.find("button", attrs={"data-bs-toggle": "collapse"})
        assert "d-flex" in toctitle["class"]
        assert toctitle.find("h4")

        top_ul, nested_ul = toc.find_all("ul")
        assert top_ul["class"] == ["collapse", "list-unstyled"]

        assert not nested_ul.get("class")

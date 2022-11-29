from collections import OrderedDict

from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from dbentry import models as _models


def concat(objects, sep="; "):
    return sep.join(str(o) for o in objects if o)


def _get_array(path, ordering=None):
    """Return a Postgres ArrayAgg aggregation on 'path'."""
    if not ordering:
        ordering = path
    return ArrayAgg(path, distinct=True, ordering=ordering)


def _get_fields(model):
    def label(field):
        if field.many_to_many or not field.concrete:
            return field.related_model._meta.verbose_name_plural
        else:
            return capfirst(field.verbose_name or field.replace('_', ' '))
    r = ""
    r += f"\tObjekt: {model._meta.verbose_name},\n"
    r += f"\tID: None,\n"
    for field in model._meta.get_fields():
        if field.name.startswith('_') or field.primary_key:
            continue
        r += f"\t{label(field)}: None,\n"
    return "OrderedDict({\n" + f"{r}" + "})"


registry = {}


def register(cls):
    registry[cls.model] = cls()
    return cls


def get_documents(queryset):
    # return registry[queryset.model].get_documents(queryset)
    result = ""
    for doc in registry[queryset.model].get_documents(queryset):
        if result:
            result += "<hr>"
        for k, v in doc.items():
            element = f"<p>{k}: {v}</p>"
            result += element
    return mark_safe(result)


class Document:
    select_related = None
    prefetch_related = None

    def get_annotations(self) -> dict:
        return {}

    def modify_queryset(self, queryset):
        """Modify the root queryset (f.ex. add annotations)."""
        if self.select_related:
            queryset = queryset.select_related(*self.select_related)
        if self.prefetch_related:
            queryset = queryset.prefetch_related(*self.prefetch_related)
        return queryset.annotate(**self.get_annotations())

    def get_document(self, obj):
        raise NotImplementedError("Subclasses must implement this method.")

    def get_documents(self, queryset):
        for obj in self.modify_queryset(queryset):
            yield self.get_document(obj)


@register
class ArtikelDocument(Document):
    model = _models.Artikel
    select_related = ['ausgabe']

    def get_annotations(self) -> dict:
        return {
            'autor_list': _get_array('autor___name'),
            'musiker_list': _get_array('musiker__kuenstler_name'),
            'band_list': _get_array('band__band_name'),
            'schlagwort_list': _get_array('schlagwort__schlagwort'),
            'genre_list': _get_array('genre__genre'),
            'ort_list': _get_array('ort___name'),
            'spielort_list': _get_array('spielort__name'),
            'person_list': _get_array('person___name')
        }

    def get_document(self, obj) -> dict:
        return OrderedDict({
            'Objekt': self.model._meta.verbose_name,
            'ID': obj.pk,
            'Ausgabe': f"{obj.ausgabe} ({obj.ausgabe.magazin})",
            'Schlagzeile': obj.schlagzeile,
            'Seite': f"{obj.seite}{obj.seitenumfang}",
            'Zusammenfassung': obj.zusammenfassung,
            'Beschreibung': obj.beschreibung,
            'Autoren': concat(obj.autor_list),
            'Musiker': concat(obj.musiker_list),
            'Bands': concat(obj.band_list),
            'Genres': concat(obj.genre_list),
            'Veranstaltungen': concat(
                f"{v.name} ({v.spielort})" for v in obj.veranstaltung.order_by('name')
            ),
            'Personen': concat(obj.person_list),
        })


@register
class AusgabeDocument:
    model = _models.Ausgabe


@register
class BandDocument:
    model = _models.Band


@register
class MusikerDocument:
    model = _models.Musiker


@register
class GenreDocument:
    model = _models.Genre

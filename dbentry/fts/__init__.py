"""
This package implements postgres text search.

This package adds a SearchVectorField with WeightedColumns and a QuerySet mixin
for django's postgres full text search. This package builds upon the python
package ``django-tsvector-field``, and extends it by allowing setting the
'language' (i.e. postgres search config) on a per-WeightedColumn basis instead
of on a per-SearchVectorField basis.
Furthermore, search vector fields of related models can now be included in
queries.

To that end, changes had to be made to the database triggers added by
django-tsvector-field: the vector field arguments 'language' and
'language_column' are ignored and only the language argument of the
WeightedColumn declarations matters.
"""

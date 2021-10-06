"""
This package adds a SearchVectorField with WeightedColumns and a QuerySet mixin
for django's postgres full text search. This package builds upon the python
package ``django-tsvector-field``, and extends it by allowing setting the
'language' (i.e. postgres search config) of each column of a SearchVectorField.
"""
"""
In detail:
django-tsvector-field's SearchVectorField implementation allows for 'language'
and 'language_column' (the name of a column in the table that specifies the 
language) arguments that set the language for the entire field.
That language is then used on every column - meaning that every column of the
field will be parsed (``to_tsvector``) using the same language/config.

But we need to able to have columns with different languages contributing to
the same search vector:
assuming that a table is about books with fields for title and summary, 
then the title of the book must not be stemmed (i.e. 'simple' must be used as 
config), while the summary of that book should be parsed according to the
appropriate natural language.

This package adds that 'per column language'. To that end, changes had to be 
made to the database triggers added by django-tsvector-field: 
the vector field arguments 'language' and 'language_column' are ignored and 
only the language argument of the WeightedColumn declarations matters.
"""

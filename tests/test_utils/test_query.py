from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Func, Value

from dbentry.utils.query import to_array, array_to_string, concatenate, limit, join_arrays, array_remove
from tests.case import MIZTestCase, DataTestCase
from tests.model_factory import make
from tests.test_utils.models import Band, Audio


class TestFunctions(MIZTestCase):
    def test_array(self):
        expr = to_array("field__path", ordering="order__field")
        self.assertIsInstance(expr, ArrayAgg)
        self.assertEqual(expr.source_expressions, [F("field__path")])
        self.assertEqual(expr.order_by.source_expressions, [F("order__field")])

    def test_join_arrays(self):
        expr = join_arrays(ArrayAgg("field_1"), ArrayAgg("field_2"))
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra, {"function": "array_cat"})
        array_1, array_2 = expr.get_source_expressions()
        self.assertEqual(array_1.source_expressions, [F("field_1")])
        self.assertEqual(array_2.source_expressions, [F("field_2")])

    def test_array_remove(self):
        expr = array_remove(ArrayAgg("array"), remove="spam")
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra, {"function": "array_remove"})
        array_expr, remove = expr.get_source_expressions()
        self.assertEqual(remove, Value("spam"))
        self.assertIsInstance(array_expr, ArrayAgg)

    def test_array_to_string(self):
        expr = array_to_string(ArrayAgg("field__path"), sep=";")
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra, {"function": "array_to_string"})

        array_expr, sep, null = expr.get_source_expressions()
        self.assertEqual(sep, Value(";"))
        self.assertEqual(null, Value("-"))
        self.assertIsInstance(array_expr, ArrayAgg)

    def test_array_to_string_multiple_arrays(self):
        expr = array_to_string(ArrayAgg("field_1"), ArrayAgg("field_2"), sep=";")
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra["function"], "array_to_string")

        remove_expr, sep, null = expr.get_source_expressions()
        self.assertEqual(sep, Value(";"))
        self.assertEqual(null, Value("-"))
        self.assertEqual(remove_expr.extra, {"function": "array_remove"})
        self.assertEqual(remove_expr.get_source_expressions()[0].extra["function"], "array_cat")

    def test_limit(self):
        expr = limit("some_expr", length=1)
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra, {"function": "left"})
        string_expr, length = expr.get_source_expressions()
        self.assertEqual(length, Value(1))

    def test_concatenate(self):
        expr = concatenate(F("field_1"), F("field_2"), sep=";")
        self.assertIsInstance(expr, Func)
        self.assertEqual(expr.extra, {"function": "concat_ws"})
        sep, string_expr1, string_expr2 = expr.get_source_expressions()
        self.assertEqual(sep, Value(";"))
        self.assertEqual(string_expr1, F("field_1"))
        self.assertEqual(string_expr2, F("field_2"))


class TestQueryset(DataTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        make(Band, musiker__kuenstler_name=["Ringo Starr", "Paul McCartney", "John Lennon"])
        make(Audio, musiker__kuenstler_name=["Ringo Starr", "Paul McCartney", "John Lennon"])

    def test_array_to_string(self):
        queryset = Band.objects.annotate(members=limit(array_to_string(to_array("musiker__kuenstler_name"))))
        self.assertEqual(queryset.get().members, "John Lennon, Paul McCartney, Ringo Starr")

    def test_array_to_string_multiple_arrays(self):
        queryset = Audio.objects.annotate(
            kuenstler=limit(array_to_string(to_array("band__band_name"), to_array("musiker__kuenstler_name"), null=""))
        )
        self.assertEqual(queryset.get().kuenstler, "John Lennon, Paul McCartney, Ringo Starr")
        queryset = Audio.objects.annotate(
            kuenstler=limit(array_to_string(to_array("musiker__kuenstler_name"), to_array("band__band_name"), null=""))
        )
        self.assertEqual(queryset.get().kuenstler, "John Lennon, Paul McCartney, Ringo Starr")

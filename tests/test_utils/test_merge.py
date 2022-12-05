from django.contrib.contenttypes.models import ContentType
from django.db import models

from dbentry import utils
from tests.case import DataTestCase, LoggingTestMixin, RequestTestCase
from tests.model_factory import make


class Foo(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Foo'


class Bar(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Bar'


class UnusedRelation(models.Model):
    base = models.ForeignKey('MergeBase', on_delete=models.CASCADE)


class BarM2M(models.Model):
    base = models.ForeignKey('MergeBase', on_delete=models.PROTECT)
    bar = models.ForeignKey('Bar', on_delete=models.PROTECT)

    class Meta:
        unique_together = (('base', 'bar'),)
        verbose_name = 'MergeBase-Bar'

    def __str__(self):
        return str(self.bar)


class MergeBase(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    foo = models.ManyToManyField('Foo')
    bar = models.ManyToManyField('Bar', through=BarM2M)

    def __str__(self):
        return self.name


class TestMerge(LoggingTestMixin, DataTestCase, RequestTestCase):
    model = MergeBase

    def setUp(self):
        super().setUp()
        # Need to clear the cache between test methods, or LogEntry queries
        # will be made with wrong ContentType ids.
        ContentType.objects.clear_cache()

    @classmethod
    def setUpTestData(cls):
        cls.foo_original = make(Foo, name='Original foo')
        cls.bar_original = make(Bar, name='Original bar')
        cls.obj1 = make(MergeBase, name='Original')
        cls.obj1.foo.add(cls.foo_original)  # noqa
        cls.obj1.bar.add(cls.bar_original)  # noqa

        cls.foo_merger1 = make(Foo, name='Foo merger One')
        cls.bar_merger1 = make(Bar, name='Bar merger One')
        cls.obj2 = make(MergeBase, name='Merger1')
        cls.obj2.foo.add(cls.foo_merger1)  # noqa
        cls.obj2.bar.add(cls.bar_merger1)  # noqa

        cls.foo_merger2 = make(Foo, name='Foo merger Two')
        cls.bar_merger2 = make(Bar, name='Bar merger Two')
        cls.obj3 = make(MergeBase, name='Merger2', description="Hello!")
        cls.obj3.foo.add(cls.foo_merger2)  # noqa
        cls.obj3.bar.add(cls.bar_merger2)  # noqa
        # Add a 'duplicate' related object to test handling of UNIQUE CONSTRAINTS
        # violations.
        cls.obj3.foo.add(cls.foo_merger1)  # noqa

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]  # noqa
        super().setUpTestData()

    def test_merge(self):
        utils.merge_records(original=self.obj1, queryset=self.model.objects.all())
        self.assertSequenceEqual(self.model.objects.all(), [self.obj1])
        self.assertSequenceEqual(
            self.obj1.foo.all(),
            [self.foo_original, self.foo_merger1, self.foo_merger2]
        )
        self.assertSequenceEqual(
            self.obj1.bar.all(),
            [self.bar_original, self.bar_merger1, self.bar_merger2]
        )

    def test_merge_records_expand(self):
        """
        Assert that merge expands the original's values when expand_original is
        True.
        """
        new_original: MergeBase
        new_original, update_data = utils.merge_records(
            original=self.obj1,
            queryset=self.queryset,
            expand_original=True,
            user_id=self.super_user.pk
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.name, 'Original')
        self.assertEqual(new_original.description, 'Hello!')
        self.assertLoggedChange(
            new_original,
            change_message=[{'changed': {'fields': ['Description']}}]
        )

    def test_merge_records_no_expand(self):
        """
        Assert that merge does not expand the original's values when
        expand_original is False.
        """
        new_original: MergeBase
        new_original, update_data = utils.merge_records(
            self.obj1,
            self.queryset,
            expand_original=False,
            user_id=self.super_user.pk
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.name, 'Original')
        self.assertNotEqual(new_original.description, 'Hello!')

    def test_related_changes(self):
        """
        Assert that merge adds all the related objects of the other objects to
        the 'original'.
        """
        _new_original, _update_data = utils.merge_records(
            self.obj1,
            self.queryset,
            expand_original=False,
            user_id=self.super_user.pk
        )
        change_message = {"name": "", "object": ""}
        added = [{"added": change_message}]

        change_message['name'] = 'MergeBase-Bar'
        self.assertIn(self.bar_original, self.obj1.bar.all())
        self.assertIn(self.bar_merger1, self.obj1.bar.all())
        change_message["object"] = str(self.bar_merger1)
        self.assertLoggedAddition(self.obj1, change_message=str(added).replace("'", '"'))
        self.assertIn(self.bar_merger2, self.obj1.bar.all())
        change_message["object"] = str(self.bar_merger2)
        self.assertLoggedAddition(self.obj1, change_message=str(added).replace("'", '"'))
        self.assertEqual(self.obj1.bar.all().count(), 3)

        change_message['name'] = 'Foo'
        self.assertIn(self.foo_original, self.obj1.foo.all())
        self.assertIn(self.foo_merger1, self.obj1.foo.all())
        change_message["object"] = str(self.foo_merger1)
        self.assertLoggedAddition(self.obj1, change_message=str(added).replace("'", '"'))
        self.assertIn(self.foo_merger2, self.obj1.foo.all())
        change_message["object"] = str(self.foo_merger2)
        self.assertLoggedAddition(self.obj1, change_message=str(added).replace("'", '"'))
        self.assertEqual(self.obj1.foo.all().count(), 3)

    def test_rest_deleted(self):
        """Assert that merge deletes the other objects."""
        utils.merge_records(
            self.obj1,
            self.queryset,
            expand_original=True,
            user_id=self.super_user.pk
        )
        self.assertNotIn(self.obj2, self.model.objects.all())
        self.assertNotIn(self.obj3, self.model.objects.all())

    def test_duplicate_protected_related_object(self):
        """
        Assert that a ProtectedError is raised if any of the related objects
        are protected and could not be deleted or could not be moved.
        """
        # Add an object to obj3 that would violate unique constraints of obj2:
        self.obj3.bar.add(self.bar_merger1)  # noqa
        queryset = self.queryset.filter(pk__in=[self.obj2.pk, self.obj3.pk])
        with self.assertRaises(models.deletion.ProtectedError):
            utils.merge_records(
                self.obj2, queryset, expand_original=True, user_id=self.super_user.pk
            )
            # Check that the merge was aborted and obj3 was not deleted:
            self.assertTrue(self.model.objects.filter(pk=self.obj3.pk).exists())

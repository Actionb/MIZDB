class Foo:
    foo: str


class Bar:
    bar: str


class _FooBar(Foo, Bar):
    pass


class UsesFooBar:

    def __init__(self, foobar: _FooBar) -> None:
        self.foo = foobar.foo
        self.bar = foobar.bar

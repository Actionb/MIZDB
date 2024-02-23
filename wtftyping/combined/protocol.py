class UsesFooBar:

    def __init__(self, foobar: "_FooBar") -> None:
        self.foobar = foobar
        self.foo = foobar.foo
        self.bar = foobar.bar



class Foo:
    foo: str


class Bar:
    bar: str


class _FooBar(Foo, Bar):
    pass

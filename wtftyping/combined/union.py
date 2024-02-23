from typing import Union


class Foo:
    foo: str


class Bar:
    bar: str


FooBar = Union[Foo, Bar]


class UsesFooAndBar:

    def __init__(self, foobar: FooBar) -> None:
        self.foo = foobar.foo
        self.bar = foobar.bar

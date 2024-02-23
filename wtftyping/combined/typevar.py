from typing import Union, TypeVar


class Foo:
    foo: str


class Bar:
    bar: str


_FooBar = TypeVar("_FooBar", bound=Union[Foo, Bar])


class UsesFooBar:

    def __init__(self, foobar: _FooBar) -> None:
        self.foo = foobar.foo
        self.bar = foobar.bar

from typing import Union, TypeVar, Generic


class Foo:
    foo: str


class Bar:
    bar: str


_FooBar = TypeVar("_FooBar", bound=Union["Foo", "Bar"])


class UsesFooAndBar:

    def __init__(self, foobar: Union["Foo", "Bar"]) -> None:
        self.foo = foobar.foo
        self.bar = foobar.bar

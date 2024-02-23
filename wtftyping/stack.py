from typing import List, Generic, TypeVar

T = TypeVar('T')


class Stack(Generic[T]):
    def __init__(self) -> None:
        self._values: List[T] = []

    def __repr__(self) -> str:
        return f'Stack{self._values!r}'

    def push(self, value: T) -> None:
        self._values.append(value)

    def pop(self) -> T:
        if len(self._values) == 0:
            raise RuntimeError('Underflow!')

        return self._values.pop()


stack: Stack[int] = Stack()
print(stack)  # Stack[]

stack.push(2)
stack.push(10)
print(stack)  # Stack[2, 10]

print(stack.pop())  # 10
print(stack)  # Stack[2]
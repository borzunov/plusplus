import pytest

from bytecode import Bytecode, Instr

from plusplus import enable_increments


@enable_increments
def test_locals():
    x = y = 42

    # In separate operations
    ++x
    assert x == 43
    --y
    assert y == 41

    # In the `assert` expression
    assert ++x == 44
    assert --y == 40

    # In the separate expression
    expression = (++x) * 2
    assert (++x) * 10 == 460
    assert x == 46


global_var = 777


@enable_increments
def test_globals():
    before = global_var

    # No need to declare `global global_var` (contrary to the `global_var += 1` statement)
    ++global_var
    assert global_var == before + 1

    assert ++global_var == before + 2
    assert global_var == before + 2


@enable_increments
def test_closures():
    free_var = 123

    # No need to specify @enable_increments for nested functions

    def closure():
        # No need to declare `nonlocal free_var` (contrary to the `free_var += 1` statement)
        ++free_var
        return ++free_var

    assert closure() == 125
    assert free_var == 125

    ++free_var
    assert ++free_var == 127
    assert free_var == 127


@enable_increments
def test_lambdas():
    free_var = 123

    # No need to call enable_increments() for nested lambdas

    pure = lambda x: ++x
    assert pure(42) == 43

    closure = lambda: ++free_var
    assert closure() == 124
    assert free_var == 124


@enable_increments
def test_subscriptions():
    arr = [1, 2]
    ++arr[0]
    assert arr[0] == 2
    assert ++arr[1] == 3
    assert arr[1] == 3

    dictionary = {'key1': 3, 'key2': 4}
    ++dictionary['key1']
    assert dictionary['key1'] == 4
    assert ++dictionary['key2'] == 5
    assert dictionary['key2'] == 5


@enable_increments
def test_subscription_expressions():
    arr = [42] * 10

    # Decrement every even element
    idx = -1
    for _ in range(5):
        --arr[(++idx) * 2]

    assert arr == [41, 42] * 5


class ClassWithOneField:
    def __init__(self, value):
        self.field = value


@enable_increments
def test_attributes():
    obj = ClassWithOneField(10)
    ++obj.field
    assert obj.field == 11
    assert ++obj.field == 12
    assert obj.field == 12

    assert ++ClassWithOneField(20).field == 21


@enable_increments
def test_list_comprehensions():
    j = 0
    assert [++j for _ in range(10)] == list(range(1, 11))


@enable_increments
def test_generators():
    def generator():
        i = 0
        for _ in range(10):
            yield ++i

    assert list(generator()) == list(range(1, 11))

    j = 0
    assert list(++j for _ in range(10)) == list(range(1, 11))


@enable_increments
def make_incrementer():
    # To decorate all class methods and the class body automatically, move the class definition
    # into a function decorated with @enable_increments

    class Incrementer:
        def __init__(self, value):
            self.field = value

        def increment_field(self):
            ++self.field

        def increment_field_and_return(self):
            return ++self.field

        @staticmethod
        def increment_and_return(x):
            return ++x

        CONSTANT = 777
        ++CONSTANT

    return Incrementer

Incrementer = make_incrementer()


def test_nested_class():
    obj = Incrementer(10)

    obj.increment_field()
    assert obj.field == 11

    assert obj.increment_field_and_return() == 12
    assert obj.field == 12

    assert Incrementer.increment_and_return(42) == 43

    assert Incrementer.CONSTANT == 778


def test_decorated_class():
    with pytest.raises(ValueError):
        @enable_increments
        class DecoratedClass:
            def method(self, x):
                return ++x


def test_syntax_errors():
    def increment_constant():
        ++'non-incrementable'

    with pytest.raises(SyntaxError):
        enable_increments(increment_constant)

    def increment_expression():
        x = 2
        ++(x + 2)

    with pytest.raises(SyntaxError):
        enable_increments(increment_expression)


def test_expected_ops_are_used():
    tested_ops = {
        'LOAD_FAST': [test_locals],
        'LOAD_GLOBAL': [test_globals],
        'LOAD_DEREF': [test_closures, test_lambdas],

        'LOAD_ATTR': [test_attributes],
        'BINARY_SUBSCR': [test_subscriptions, test_subscription_expressions],

        'MAKE_FUNCTION': [test_closures, test_lambdas, test_generators, make_incrementer],
    }

    for op, tests in tested_ops.items():
        for test_func in tests:
            assert any(item.name == op
                       for item in Bytecode.from_code(test_func.__code__)
                       if isinstance(item, Instr)), \
                '{} expected to have {}'.format(test_func.__name__, op)

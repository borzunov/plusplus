# Situations where increments may be useful

This list shows situations where increments (if used with care) may allow to avoid repetitions or
make code more readable. Each situation is demonstrated by an example of the code from the Python standard
library to ensure that this situation is realistic (this approach is inspired by
the ["Importance of real code"](https://www.python.org/dev/peps/pep-0572/#the-importance-of-real-code) section of
PEP 572 "Assignment Expressions"). Only one example is shown for clarity, however the standard
library typically contains many similar examples.

By providing this list, I do not claim that using increments and/or allowing them makes Python code better in general.
See the description of possible risks [here](../README.md#why).

## 1. if conditions

- Source: [multiprocessing/managers.py](https://github.com/python/cpython/blob/d0978761118856e8ca8ea7b162a6585b8da83df9/Lib/multiprocessing/managers.py#L453)

    Current:

    ```python
    self.id_to_refcount[ident] -= 1
    if self.id_to_refcount[ident] == 0:
        del self.id_to_refcount[ident]
    ```

    Improved:

    ```python
    if --self.id_to_refcount[ident] == 0:
        del self.id_to_refcount[ident]
    ```

    This allows to avoid repeating the long subscription expression.

## 2. while conditions

- Source: [unittest/util.py](https://github.com/python/cpython/blob/bb3e0c240bc60fe08d332ff5955d54197f79751c/Lib/unittest/util.py#L66)

    Current:

    ```python
    e = expected[i]
    a = actual[j]
    if e < a:
        missing.append(e)
        i += 1
        while expected[i] == e:
            i += 1
    elif e > a:
        unexpected.append(a)
        j += 1
        while actual[j] == a:
            j += 1
    else:
        i += 1
        try:
            while expected[i] == e:
                i += 1
        finally:
            j += 1
            while actual[j] == a:
                j += 1
    ```

    Improved:

    ```python
    e = expected[i]
    a = actual[j]
    if e < a:
        missing.append(e)
        while expected[++i] == e:
            pass
    elif e > a:
        unexpected.append(a)
        while actual[++j] == a:
            pass
    else:
        try:
            while expected[++i] == e:
                pass
        finally:
            while actual[++j] == a:
                pass
    ```

    This allows to make code much shorter.

## 3. Incrementing callbacks

- Source: [test/test_weakref.py](https://github.com/python/cpython/blob/2a8127cafe1d196f858a3ecabf5f1df3eebf9a12/Lib/test/test_weakref.py#L1064)

    Current:

    ```python
    def callback(w):
        self.cbcalled += 1

    o = C()
    r1 = MyRef(o, callback)
    r1.o = o
    del o
    ```

    Improved:

    ```python
    o = C()
    r1 = MyRef(o, lambda: ++self.cbcalled)
    r1.o = o
    del o
    ```

    This allows to avoid the full function definition in a separate place.

## 4. Handmade enums

- Source: [distutils/log.py](https://github.com/python/cpython/blob/d0978761118856e8ca8ea7b162a6585b8da83df9/Lib/distutils/log.py#L6)

    Current:

    ```python
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    FATAL = 5
    ```

    Improved:

    ```python
    _index = 0
    DEBUG = ++_index
    INFO = ++_index
    WARN = ++_index
    ERROR = ++_index
    FATAL = ++_index
    ```

    This makes adding new values and reordering the existing ones easier.

from collections import namedtuple
from types import CodeType

from bytecode import Bytecode, Instr, SetLineno


def patch_code(code):
    bytecode = Bytecode.from_code(code)
    new_bytecode = []

    index = 0
    while index < len(bytecode):
        patch = patch_increment_region(bytecode[index:index + 7], code)
        if patch is None:
            patch = patch_load_code_region(bytecode[index:index + 1])
        if patch is None:
            patch = Patch(n_removed=1, added=[bytecode[index]])

        index += patch.n_removed
        new_bytecode.extend(patch.added)

    bytecode.clear()
    bytecode.extend(new_bytecode)
    return bytecode.to_code()


Patch = namedtuple('Patch', ['n_removed', 'added'])


def patch_increment_region(region, code):
    n_removed = 3

    if is_pytest_intermediate_value_capturing(region[1:3]):
        # Remove capturing of the LOAD_ATTR/BINARY_SUBSCR result
        region[1:3] = []
        n_removed += 2
    if is_pytest_intermediate_value_capturing(region[2:4]):
        # Remove capturing of the first UNARY_POSITIVE/NEGATIVE result
        region[2:4] = []
        n_removed += 2

    if not (len(region) >= 3 and
            all(isinstance(item, Instr) for item in region[:3]) and
            region[1].name in UNARY_TO_INPLACE_OP and
            region[1].name == region[2].name):
        return None
    load_instr, unary_instr = region[:2]

    if load_instr.name not in LOAD_TO_STORE_OP:
        raise make_syntax_error('Increment/decrement may be applied only to a variable, '
                                'a subscriptable item, or an attribute', load_instr.lineno, code)

    repl = [SetLineno(load_instr.lineno)]
    repl += PRE_LOAD_HOOK.get(load_instr.name, [])
    repl += [
        load_instr,
        Instr('LOAD_CONST', 1),
        Instr(UNARY_TO_INPLACE_OP[unary_instr.name]),
        Instr('DUP_TOP'),  # One to store, one to return
    ]

    store_op = LOAD_TO_STORE_OP[load_instr.name]
    repl += PRE_STORE_HOOK.get(store_op, [])
    repl.append(Instr(store_op, load_instr.arg))

    return Patch(n_removed=n_removed, added=repl)


def patch_load_code_region(region):
    if not (isinstance(region[0], Instr) and
            region[0].name == 'LOAD_CONST' and
            isinstance(region[0].arg, CodeType)):
        return None
    load_const_instr = region[0]

    repl = [
        Instr('LOAD_CONST', patch_code(load_const_instr.arg), lineno=load_const_instr.lineno),
    ]
    return Patch(n_removed=1, added=repl)


def make_syntax_error(message, lineno, code):
    return SyntaxError('File "{}", line {}, in {}: {}'.format(
        code.co_filename, lineno, code.co_name, message))


def is_pytest_intermediate_value_capturing(region):
    """
    pytest rewrites asserts in test functions to save each intermediate result of the expressions.
    This divides consecutive ops (e.g. two UNARY_POSITIVE ops) with STORE_FAST and LOAD_FAST
    to dump the intermediate result that doesn't usually make sense in our case.

    See https://docs.pytest.org/en/stable/assert.html#assertion-introspection-details
    """

    return (all(isinstance(item, Instr) for item in region) and
            [item.name for item in region] == ['STORE_FAST', 'LOAD_FAST'] and
            region[0].arg == region[1].arg and
            region[0].arg.startswith('@py_assert'))


UNARY_TO_INPLACE_OP = {
    'UNARY_POSITIVE': 'INPLACE_ADD',
    'UNARY_NEGATIVE': 'INPLACE_SUBTRACT',
}

LOAD_TO_STORE_OP = {
    'LOAD_DEREF': 'STORE_DEREF',
    'LOAD_FAST': 'STORE_FAST',
    'LOAD_GLOBAL': 'STORE_GLOBAL',
    'LOAD_NAME': 'STORE_NAME',

    'LOAD_ATTR': 'STORE_ATTR',
    'BINARY_SUBSCR': 'STORE_SUBSCR',
}

PRE_LOAD_HOOK = {
    'LOAD_ATTR': [
        # Stack: [..., obj] -> [..., obj, obj]
        Instr('DUP_TOP'),
    ],
    'BINARY_SUBSCR': [
        # Stack: [..., arr, idx] -> [..., (arr, idx), arr, idx]
        Instr('DUP_TOP_TWO'),
        Instr('BUILD_TUPLE', 2),
        Instr('ROT_THREE'),
    ],
}

PRE_STORE_HOOK = {
    'STORE_ATTR': [
        # Stack: [..., obj, value, value] -> [value, value, obj]
        Instr('ROT_THREE'),
        Instr('ROT_THREE'),
    ],
    'STORE_SUBSCR': [
        # Stack: [..., (arr, idx), value, value] -> [..., value, value, arr, idx]
        Instr('ROT_THREE'),
        Instr('ROT_THREE'),
        Instr('UNPACK_SEQUENCE', 2),
        Instr('ROT_TWO'),
    ],
}

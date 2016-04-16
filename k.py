import operator

def node(name, props):
    def set_props(self, *propvs):
        for prop, value in zip(props.split(), propvs):
            setattr(self, prop, value)
    return type(name, (Node,), {"__init__": set_props,
                                "__repr__": lambda self: "<%s: %s>" % (name, " ".join("%s=%r" % (k,v) for k,v in self.__dict__.items())),
                                "__eq__": lambda self, other: self.__class__.__name__ == other.__class__.__name__ and self.__dict__ == other.__dict__
                                })

class Node: pass
Num = node('Num', 'v')
List = node('List', 'v')
DyadApply = node('DyadApply', 'l op r')

is_ = isinstance

class InternalError(Exception): pass
class GeneralError(Exception): pass
class TypeError(Exception): pass
class LengthError(Exception): pass

def to_k(v):
    if isinstance(v, int) or isinstance(v, float): return Num(v)
    if isinstance(v, list): return List(list(map(to_k, v)))
    raise InternalError("to_k: unhandled value " + repr(v))

def from_k(v):
    if is_(v, Num): return v.v
    if is_(v, List): return v.v
    raise InternalError("from_k: unhandled value " + repr(v))

def to_dyad(f):
    "Lifts a binary Python function into a boxed dyadic function"
    return lambda x,y: to_k(f(from_k(x), from_k(y)))

def nums(*args): return list(map(Num, args))

def recursive_shape(v):
    "A helper function for returning the shape of possibly nested lists, for the purpose of comparing list shapes."
    if not is_(v, List): return 0
    return list(map(recursive_shape, v.v))

def op_plus(x, y):
    if is_(x, Num) and is_(y, Num): return Num(x.v + y.v)
    if is_(x, List) and is_(y, List):
        if recursive_shape(x) == recursive_shape(y): return List([op_plus(a, b) for a, b in zip(x.v, y.v)])
        else: raise LengthError(x, y)
    raise TypeError(x, y)

def apply_dyad(expr):
    return {"+": op_plus
           }[expr.op](expr.l, expr.r)

def eval(expr):
    if is_(expr, Num): return expr
    if is_(expr, DyadApply): return apply_dyad(expr)
    raise InternalError("unhandled expr: " + repr(expr))

_testsSucceeded = 0
_testsFailed = 0

def teq(expr, expected):
    global _testsSucceeded, _testsFailed
    v = eval(expr)
    if not isinstance(expected, Node):
        expected = to_k(expected)
    if v != expected:
        print("FAIL: Got %r, expected %r" % (v, expected))
        _testsFailed += 1
    else: _testsSucceeded += 1

def terr(expr, exc):
    global _testsSucceeded, _testsFailed
    try: eval(expr)
    except Exception as e:
        if not isinstance(e, exc):
            print("FAIL: Expected failure with %r, got failure with %r" % (exc, e))
            _testsFailed += 1
        else:
            _testsSucceeded += 1
    else:
        print("FAIL: Expected failure with %r, but succeeded" % exc)
        _testsFailed += 1

def tests():
    teq( DyadApply(Num(42), '+', Num(8)), 50 )
    teq( DyadApply(List(nums(1, 2, 3)), '+', List(nums(10, 11, 12))), [11, 13, 15] )
    terr( DyadApply(List(nums(1, 2, 3)), '+', List(nums(10, 11))), LengthError )

    # list length
    assert recursive_shape(List([])) == []
    assert recursive_shape(List([Num(1)])) == [0]
    assert recursive_shape(List(nums(1, 2, 3))) == [0, 0, 0]

    # multi-dimensional lists

    # 2x2 list/matrix
    matrix = List([List(nums(1, 2)),
                   List(nums(3, 4))])

    assert recursive_shape(matrix) == [[0, 0], [0, 0]]

    teq( DyadApply(matrix, '+', matrix), [[2,4], [6,8]] ) # double matrix
    terr( DyadApply(matrix, '+', to_k([[2,4], [6,8,9]])), LengthError )

    # more complex list
    assert recursive_shape(List( [List([Num(1), List(nums(10, 11)), Num(3)]),
                                  List(nums(3, 4, 5, 6, 7))] )) == [[0, [0, 0], 0], [0, 0, 0, 0, 0]]

    print("%d tests succeeded, %d tests failed" % (_testsSucceeded, _testsFailed))

def main():
    tests()

if __name__ == "__main__": main()
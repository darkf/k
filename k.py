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

def op_plus(x, y):
    if is_(x, Num) and is_(y, Num): return Num(x.v + y.v)
    if is_(x, List) and is_(y, List):
        if len(x.v) == len(y.v): return List([op_plus(a, b) for a, b in zip(x.v, y.v)])
        else: raise LengthError(x, y)
    raise InternalError("op_plus")

def apply_dyad(expr):
    return {"+": op_plus
           }[expr.op](expr.l, expr.r)

def eval(expr):
    if is_(expr, Num): return expr
    if is_(expr, DyadApply): return apply_dyad(expr)
    raise InternalError("unhandled expr: " + repr(expr))

def teq(expr, expected):
    v = eval(expr)
    if not isinstance(expected, Node):
        expected = to_k(expected)
    if v != expected:
        print("FAIL: Got %r, expected %r" % (v, expected))

def terr(expr, exc):
    try: eval(expr)
    except Exception as e:
        if not isinstance(e, exc):
            print("FAIL: Expected failure with %r, got failure with %r" % (exc, e))
    else: print("FAIL: Expected failure with %r, but succeeded" % exc)

def tests():
    teq( DyadApply(Num(42), '+', Num(8)), 50 )
    teq( DyadApply(List(nums(1, 2, 3)), '+', List(nums(10, 11, 12))), [11, 13, 15] )
    terr( DyadApply(List(nums(1, 2, 3)), '+', List(nums(10, 11))), LengthError )

def main():
    tests()

if __name__ == "__main__": main()
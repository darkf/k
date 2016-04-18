import operator, math, collections

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
Char = node('Char', 'v')
List = node('List', 'v')
DyadApply = node('DyadApply', 'l op r')
MonadApply = node('MonadApply', 'op v')
AdverbMonadApply = node('AdverbMonadApply', 'adv op v')
AdverbDyadApply = node('AdverbDyadApply', 'adv l op r')
Function = node('Function', 'args body')
Var = node('Var', 'name')
Verb = node('Verb', 'name forcemonad')
Assign = node('Assign', 'name v')

Num.__lt__ = lambda self, other: self.v < other.v
Char.__lt__ = lambda self, other: self.v < other.v

is_ = isinstance

def newEnv(): return [{}]
def pushScope(): env.insert(0, {})
def popScope(): env.pop(0)
def bind(name, v):
    for e in env:
        if name in e:
            e[name] = v
            return
    env[0][name] = v
    return v
def lookup(name):
    for e in env:
        if name in e: return e[name]
    return None

env = newEnv()

def is_atom(x): return not is_(x, List)

class InternalError(Exception): pass
class GeneralError(Exception): pass
class TypeError(Exception): pass
class LengthError(Exception): pass
class BindingError(Exception): pass

def to_k(v):
    if isinstance(v, int) or isinstance(v, float): return Num(v)
    if isinstance(v, list): return List(list(map(to_k, v)))
    raise InternalError("to_k: unhandled value " + repr(v))

def from_k(v):
    if is_(v, Num): return v.v
    if is_(v, List): return list(map(from_k, v.v))
    raise InternalError("from_k: unhandled value " + repr(v))

def to_dyad(f):
    "Lifts a binary Python function into a boxed dyadic function"
    return lambda x,y: to_k(f(from_k(x), from_k(y)))

def nums(*args): return list(map(Num, args))

def recursive_shape(v):
    "A helper function for returning the shape of possibly nested lists, for the purpose of comparing list shapes."
    if not is_(v, List): return 0
    return list(map(recursive_shape, v.v))

def zip_with(f, xs, ys):
    return [f(x, y) for x, y in zip(xs, ys)]

def product(xs):
    prod = 1
    for x in xs: prod *= x
    return prod

def elementwise(f, x, y):
    if is_(x, List) and is_(y, List):
        if recursive_shape(x) == recursive_shape(y): return List(zip_with(f, x.v, y.v))
        else: raise LengthError(x, y)
    raise TypeError(x, y)

def fold(f, xs, v):
    for x in xs.v:
        v = f(x, v)
    return v

def scan(f, xs, v):
    if xs.v == []: return List([])
    r = []
    for x in xs.v:
        v = f(x, v)
        r.append(v)
    return List(r)

def op_plus(x, y):
    if is_(x, Num) and is_(y, Num): return Num(x.v + y.v)
    if is_(x, Num) and is_(y, List): return List([Num(x.v + v.v) for v in y.v])
    return elementwise(op_plus, x, y)

def op_minus(x, y):
    if is_(x, Num) and is_(y, Num): return Num(x.v - y.v)
    if is_(x, Num) and is_(y, List): return List([Num(x.v - v.v) for v in y.v])
    return elementwise(op_minus, x, y)

def op_star(x, y):
    if is_(x, Num) and is_(y, Num): return Num(x.v * y.v)
    return elementwise(op_star, x, y)

def repeat_list(x, n):
    "If the list x is shorter than n, then repeat elements of x until its length is equal to n."
    if len(x.v) < n:
        # make enough copies needed to repeat enough times for n, then
        # take exactly n items.
        copies_needed = math.ceil(n / len(x.v))
        return List((x.v*copies_needed)[:n])
    else: # take
        return List(x.v[:n])

def reshape(x, shape, start=0):
    if shape == []:
        return List([])

    if is_atom(x): # l#a
        # build a list of the atom in the desired shape
        if len(shape) == 1: # repeat
            return List([x]*shape[0])
        return List([ reshape(x, shape[1:]) for _ in range(shape[0]) ])
    elif is_(x, List): # l#l
        # print("shape:", shape)

        if len(shape) == 1: # single dimension
            end = start+shape[0]

            if len(x.v) < end: # if we need to, extend the list by repeating it
                # starting where we left off, instead of the beginning.
                x = repeat_list(x, end)
            return List( x.v[start:end] )
        else: # multi-dimensional
            # build a list of rows with incremental starting indices.
            # for each row, we increment start by the size of that row (and the sizes of all of _its_ rows, recursively)
            # so that we remember where we left off in the list in the previous row.
            rowSize = product(shape[1:])
            return List([ reshape(x, shape[1:], start=start + row*rowSize) for row in range(shape[0]) ])

def op_hash(x, y):
    if is_(x, Num): # take (n#l or n#a)
        if is_(y, List):
            xs = y.v
            if len(y.v) < x.v: # repeat
                # make enough copies needed to repeat x times, then
                # take exactly x items.
                copies_needed = math.ceil(x.v / len(y.v))
                xs = (xs*copies_needed)[:x.v]
            else: # take
                xs = xs[:x.v]
        elif is_atom(y): # repeat atom
            xs = [y]*x.v
        else: raise InternalError("")
        return List(xs)
    elif is_(x, List): # l#l or l#a (reshape)
        shape = [from_k(dim) for dim in x.v]
        return reshape(y, shape)
    return InternalError("op_hash")

def apply_fn(f, args):
    if len(f.args) != len(args):
        raise LengthError("apply_fn arg length mismatch")
    r = None # TODO: what is the default value?
    pushScope()
    for name, v in zip(f.args, args):
        bind(name, v)
    for expr in f.body:
        r = eval(expr)
    popScope()
    return r

def op_at(x, y):
    if is_(x, Function): return apply_fn(x, [y])
    raise InternalError("op_at")

def op_dot(x, y):
    if is_(x, Function) and is_(y, List): # dot-apply
        return apply_fn(x, y.v)
    if is_(x, List) and is_(y, List):
        if len(y.v) == 1 and is_(y.v[0], List): # return a list indexed into x
            return List([x.v[i.v] for i in y.v[0].v])
        else: # index at depth
            xs = x
            for i in y.v:
                print("xs:", xs, "y:", y)
                xs = xs.v[i.v]
            return xs
    raise InternalError("op_dot")

def op_underscore(x, y):
    if is_(x, Num) and is_(y, List): # drop (n_l)
        return List(y.v[x.v:])
    if is_(x, Num): return y
    raise InternalError("op_underscore")

def apply_dyad(expr):
    if is_(expr.op, Verb): expr.op = expr.op.name
    if is_(expr.op, Function): return apply_fn(expr.op, [eval(expr.l), eval(expr.r)]) # function dyad
    return {"+": op_plus, "-": op_minus, "*": op_star, "#": op_hash, "@": op_at,
            ".": op_dot, "_": op_underscore
           }[expr.op](eval(expr.l), eval(expr.r))

def op_hash_m(x): # count (#l)
    if is_(x, List): return Num(len(x.v))
    elif is_atom(x): return Num(1)
    return InternalError("")

def op_comma_m(x): # enlist (,)
    return List([x])

def op_bang_m(x):
    if is_(x, Num): # int (!n)
        return List(list(map(Num, range(x.v))))
    raise InternalError("op_bang_m")

def op_minus_m(x):
    if is_(x, Num): return Num(-x.v)
    raise InternalError("op_minus_m")

def op_star_m(x):
    if is_(x, List): return x.v[0]
    raise InternalError("op_star_m")

def op_less_than_m(x): # asc
    if is_(x, List):
        sorted_x = sorted(((v, i) for i,v in enumerate(x.v)), key=lambda x: x[0]) # x sorted, maintaining indices
        return List([Num(i) for _,i in sorted_x])
    raise InternalError("op_less_than_m")

def monadic(verb):
    # TODO: we should really use Verb everywhere
    if is_(verb, Verb): return verb.forcemonad or monadic(verb.verb)
    if is_(verb, Function): return len(verb.args) == 1
    return True # XXX

def apply_monad(expr):
    if is_(expr.op, Verb): expr.op = expr.op.name
    if is_(expr.op, Function): return apply_fn(expr.op, [eval(expr.v)]) # function monad
    return {"#": op_hash_m, ",": op_comma_m, "!": op_bang_m, "-": op_minus_m, "*": op_star_m,
            "<": op_less_than_m
           }[expr.op](eval(expr.v))

def apply_monad_adverb(expr):
    if is_(expr.op, Verb): expr.op = expr.op.name
    if expr.adv in ("/", "\\"): # over, scan
        xs = eval(expr.v)
        initial = xs.v[0]
        # special cased initial folding values
        if expr.op == "+": initial = Num(0)
        elif expr.op == "*": initial = Num(1)

        if expr.adv == "/": # over
            return fold(lambda x, acc: eval(DyadApply(acc, expr.op, x)), xs, initial)
        else:
            if monadic(expr.op): # scan-fixedpoint
                initial = xs
                r = []; v = initial; v_old = v
                while True:
                    r.append(v)
                    v = eval(MonadApply(expr.op, v))
                    if v == v_old or v == initial: break
                    v_old = v
                return List(r)
            else: # scan
                return scan(lambda x, acc: eval(DyadApply(acc, expr.op, x)), xs, initial)
    if expr.adv == "'": # each
        return List(list(map(lambda x: eval(MonadApply(expr.op, x)), eval(expr.v).v)))
    raise InternalError("apply_monad_adverb")

def eval(expr):
    if is_(expr, Num) or is_(expr, Char) or is_(expr, Function): return expr
    if is_(expr, List): return List(list(map(eval, expr.v)))
    if is_(expr, DyadApply): return apply_dyad(expr)
    if is_(expr, MonadApply): return apply_monad(expr)
    if is_(expr, AdverbMonadApply): return apply_monad_adverb(expr)
    if is_(expr, Var):
        v = lookup(expr.name)
        if v is None:
            raise BindingError("Unbound variable '%s'" % name)
        return v
    if is_(expr, Assign): return bind(expr.name, eval(expr.v))
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
    teq( DyadApply(List([]), '+', List([])), [] )
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

    teq( DyadApply(matrix, '*', matrix), [[1,4], [9,16]] ) # square the matrix elementwise
    terr( DyadApply(matrix, '*', to_k([[2,4], [6,8,9]])), LengthError )

    # more complex list
    assert recursive_shape(List( [List([Num(1), List(nums(10, 11)), Num(3)]),
                                  List(nums(3, 4, 5, 6, 7))] )) == [[0, [0, 0], 0], [0, 0, 0, 0, 0]]

    # take
    teq( DyadApply(Num(3), '#', Num(42)), [42, 42, 42] ) # n#a
    teq( DyadApply(Num(3), '#', List(nums(1, 2, 3, 4, 5))), [1, 2, 3] ) # n#l take
    teq( DyadApply(Num(5), '#', List(nums(1, 2))), [1, 2, 1, 2, 1] ) # n#l repeat

    # reshape
    teq( DyadApply(List([Num(3)]), '#', Num(5)), [ 5, 5, 5 ] ) # l#a reshape
    teq( DyadApply(List(nums(2, 2)), '#', Num(5)), [ [5, 5], [5, 5] ] ) # l#a reshape
    teq( DyadApply(List(nums(2, 2)), '#', List(nums(1, 2, 3, 4))), [ [1, 2], [3, 4] ] ) # l#a reshape (1d -> 2d)
    teq( DyadApply(List(nums(2, 2)), '#', List(nums(1, 2))), [ [1, 2], [1, 2] ] ) # l#a reshape (repeat 2d)
    teq( DyadApply(List(nums(2, 2)), '#', List(nums(1, 2, 3, 4))), [ [1, 2], [3, 4] ] ) # l#a reshape (truncating 2d)
    teq( DyadApply(List(nums(2, 3)), '#', List(nums(1, 2))), [ [1, 2, 1], [2, 1, 2] ] ) # l#a reshape (repeat 2d)
    teq( DyadApply(List(nums(2, 3)), '#', List(nums(1, 2, 3, 4))), [ [1, 2, 3], [4, 1, 2] ] ) # l#a reshape (repeat 2d)
    
    teq( DyadApply(List(nums(2, 2, 2)), '#', List(nums(1, 2, 3))), [   [[1,2],[3,1]], [[2,3],[1,2]]   ] ) # l#a reshape (repeat 3d)
    # l@a reshape (repeat 3d)
    teq( DyadApply(List(nums(2, 3, 4)), '#', List(nums(1, 2, 3))), [ [[1, 2, 3, 1],
                                                                      [2, 3, 1, 2],
                                                                      [3, 1, 2, 3]],
                                                                     [[1, 2, 3, 1],
                                                                      [2, 3, 1, 2],
                                                                      [3, 1, 2, 3]] ] )

    # l@a reshape (repeat 4d)
    teq( DyadApply(List(nums(2, 2, 2, 2)), '#', List(nums(1, 2, 3))),  [
                                                                         [[[1, 2],
                                                                           [3, 1]],
                                                                          [[2, 3],
                                                                           [1, 2]]],
                                                                         [[[3, 1],
                                                                           [2, 3]],
                                                                          [[1, 2],
                                                                           [3, 1]]] ] )

    # TODO: Test more cases of reshape

    # count
    teq( MonadApply('#', List(nums(1, 2, 3))), 3 ) # #l
    teq( MonadApply('#', Num(3)), 1 ) # #a

    # adverbs

    print("%d tests succeeded, %d tests failed" % (_testsSucceeded, _testsFailed))

def main():
    tests()

if __name__ == "__main__": main()
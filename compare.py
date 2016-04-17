# Compare our interpreter with the output of oK <https://github.com/JohnEarnest/ok>

import subprocess, json, traceback
import k, parse

def ok_eval(expr):
    try:
        expr = expr.replace("'", "\\'") # escape single quotes
        output = subprocess.check_output(["node", "-p", "var ok=require('../ok/ok'); JSON.stringify(ok.run(ok.parse('%s'), ok.baseEnv()))" % expr], stderr=subprocess.STDOUT)
        return json.loads(output.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        #print("eval error")
        return None

def eval(expr):
    v = ok_eval(expr)
    if v is None: return None
    return parse.to_ast(v)

red = "\033[91m"
green = "\033[92m"
reset = "\033[00m"

_testsSucceeded = 0
_testsFailed = 0

def t(expr):
    global _testsSucceeded, _testsFailed
    res_ok = eval(expr)
    ast = parse.parse(expr)[0]
    try:
        res_k = k.eval(ast)
    except Exception as e:
        if res_ok is None:
            # ok, both threw exceptions
            print(green+"SUCC"+reset+": Got exception %r, both failed for: %s" % (e, expr))
            _testsSucceeded += 1
            return

        print(red+"FAIL"+reset+": Got exception %r, expected %r for: %s" % (e, res_ok, expr))
        print("AST: %r" % ast)
        print("Raw AST: %s" % parse.ast(expr, raw=True))
        traceback.print_exc()
        _testsFailed += 1
        return

    if res_k != res_ok:
        print(red+"FAIL"+reset+": Got %r, expected %r for: %s" % (res_k, res_ok, expr))
        print("AST: %r" % ast)
        _testsFailed += 1
    else:
        print(green+"SUCC"+reset+": Got %r, expected %r for: %s" % (res_k, res_ok, expr))
        _testsSucceeded += 1

def tests():
    t("1+2")
    t("{{x}x}1")
    t("{x+y}[42; 8]")
    t("{{x+y}[x; y]}[42; 8]")
    return

    t("+/ 1 2 3") # sum
    t("{x}1")
    t("{x+1}1")
    t("{x*2}5")
    t("{x*x}5")
    t("{x}1 2 3")
    t("{{x}x}1")
    t("{{x*2}x*4}5")
    t("{{x*{x*5}2}x*4}5")
    t("{x*y}/ 1 2 3")
    
    return
    t("1+2")
    t("+/ 1 2 3") # sum
    t("*/ 1 2 3") # product
    t("! 3") # enumeration
    t("! 10") # enumeration
    t("1+!10") # adding to an enumeration
    t("*/1+!10") # factorial
    return

    t("1")
    t("1+2")
    t("1*2")
    t("1*2+1")

    t("42+8")
    t("1 2 3 + 10 11 12")
    t("1 2 3 + 10 11") # err
    t("() + ()")
    t("#1 2 3")

    # 2x2 matrices
    t("((1 2); (3 4))") # specifying a matrix
    t("((1 2); (3 4)) + ((1 2); (3 4))") # double matrix
    t("((1 2); (3 4)) * ((1 2); (3 4))") # squaring a matrix

    t("((1 2); (3 4)) * ((2;4); (6; 8; 9))") # length error

    # count
    t("# 1 2 3")
    t("# 3")

    # take
    t("3 # 42")
    t("3 # 1 2 3 4 5")
    t("5 # 1 2")

    # reshape
    t("(,3) # 5")
    t("2 2 # 5")
    t("2 2 # 1 2 3 4")
    t("2 2 # 1 2")
    t("2 3 # 1 2")
    t("2 3 # 1 2 3 4")

    t("2 2 2 # 1 2 3")
    t("2 3 4 # 1 2 3")

    # l@a reshape (repeat 4d)
    t("2 2 2 2 # 1 2 3")

    # l@a reshape (repeat 5d)
    t("1 2 3 4 5 # 1 2 3 4 5")

    # TODO: Test more cases of reshape

    print("")
    print("%d tests succeeded, %d tests failed" % (_testsSucceeded, _testsFailed))


if __name__ == "__main__": tests()
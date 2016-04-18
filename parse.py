# Use oK <https://github.com/JohnEarnest/ok> to parse K

import subprocess, json, sys
import k

def ast(expr, raw=False):
	try:
		expr = expr.replace("\\", "\\\\") # escape backslashes
		expr = expr.replace("'", "\\'") # escape single quotes
		output = subprocess.check_output(["node", "-p", "JSON.stringify(require('../ok/ok').parse('%s'))" % expr], stderr=subprocess.STDOUT).decode('utf-8')
		return output if raw else json.loads(output)
	except subprocess.CalledProcessError:
		print("parse error for:", expr)
		return None

def to_ast(v):
	if type(v) == str: return v
	if v['t'] == 0: return k.Num(v['v'])
	if v['t'] == 3: return k.List(list(map(to_ast, v['v'])))
	if v['t'] == 8:
		if 'r' in v: # monadic apply
			if 'l' in v and v['l'] is not None: return k.DyadApply(to_ast(v['l']), v['v'], to_ast(v['r']))
			else: return k.MonadApply(v['v'], to_ast(v['r']))
		else: # verb
			return k.Verb(v['v'])
	if v['t'] == 9:
		if 'l' in v and v['l'] is not None: return k.AdverbDyadApply(v['v'], to_ast(v['l']), to_ast(v['verb']), to_ast(v['r']))
		return k.AdverbMonadApply(v['v'], to_ast(v['verb']), to_ast(v['r']))
	if v['t'] == 5: return k.Function(v['args'], list(map(to_ast, v['v'])))
	if v['t'] == 7:
		if 'r' in v and v['r'] is not None: return k.Assign(v['v'], to_ast(v['r']))
		return k.Var(v['v'])

	raise k.InternalError("to_ast: t=%d | %r" % (v['t'], v))

def parse(expr):
	return list(map(to_ast, ast(expr)))

def main():
	#print(parse("1 # 1 2 3"))
	print(parse(sys.argv[1]))

if __name__ == "__main__": main()
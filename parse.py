# Use oK <https://github.com/JohnEarnest/ok> to parse K

import subprocess, json, sys
import k

def ast(expr):
	try:
		expr = expr.replace("'", "\\'") # escape single quotes
		output = subprocess.check_output(["node", "-p", "JSON.stringify(require('../ok/ok').parse('%s'))" % expr], stderr=subprocess.STDOUT)
		return json.loads(output.decode('utf-8'))
	except subprocess.CalledProcessError:
		print("parse error")
		return None

def to_ast(v):
	if v['t'] == 0: return k.Num(v['v'])
	if v['t'] == 3: return k.List(list(map(to_ast, v['v'])))
	if v['t'] == 8:
		if 'l' in v: return k.DyadApply(to_ast(v['l']), v['v'], to_ast(v['r']))
		else: return k.MonadApply(v['v'], to_ast(v['r']))
	if v['t'] == 9:
		if 'l' in v: return k.AdverbMonadApply(v['v'], v['verb']['v'], to_ast(v['r']))
		return k.AdverbDyadApply(v['v'], to_ast(v['l']), v['verb']['v'], to_ast(v['r']))
	if v['t'] == 5: return k.Function(v['args'], list(map(to_ast, v['v'])))
	if v['t'] == 7: return k.Var(v['v'])

	raise k.InternalError("to_ast: t=%d | %r" % (v['t'], v))

def parse(expr):
	return list(map(to_ast, ast(expr)))

def main():
	#print(parse("1 # 1 2 3"))
	print(parse(sys.argv[1]))

if __name__ == "__main__": main()
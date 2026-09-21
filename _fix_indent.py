import py_compile
try:
    py_compile.compile("ui.py", doraise=True)
    print("COMPILE OK")
except py_compile.PyCompileError as e:
    print("COMPILE ERROR: " + str(e))
    exit(1)
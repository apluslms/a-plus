import virtualenv, textwrap
output = virtualenv.create_bootstrap_script(textwrap.dedent("""

def after_install(options, home_dir):
	if sys.platform == "win32":
		bin = "Scripts"
	else:
		bin = "bin"
	subprocess.call([join(home_dir, bin, "pip"), "install", "-r", "requirements.txt"])
"""))
print(output)

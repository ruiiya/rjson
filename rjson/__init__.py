"""rjson package - small template runtime helpers and runtime API"""
from .helpers import functions, load_addon, load_addons
from .helpers import load_addons_from_dir, teardown_addons
from .template_runtime import TemplateRuntime
import yaml
import json
import os


def render_string(s, context=None):
	rt = TemplateRuntime(context or {}, functions)
	return rt.render(s)


def render_template_obj(obj, context=None):
	rt = TemplateRuntime(context or {}, functions)
	return rt.render(obj)


def load_and_render_yaml(path, context=None):
	with open(path, "r", encoding="utf-8") as f:
		tpl = yaml.safe_load(f)
	return render_template_obj(tpl, context=context)


def load_and_render_file(path, context=None):
	"""Load a YAML or JSON template file and render it.

	If the extension is .json the file is parsed as JSON, otherwise YAML is used.
	"""
	path = os.fspath(path)
	_, ext = os.path.splitext(path)
	with open(path, "r", encoding="utf-8") as f:
		if ext.lower() == ".json":
			tpl = json.load(f)
		else:
			tpl = yaml.safe_load(f)
	return render_template_obj(tpl, context=context)


def main_cli(argv=None):
	# Lightweight CLI wrapper that defers to main if present
	try:
		from . import cli as _cli
	except Exception as e:
		# CLI module not available
		print("rjson: no CLI available")
		raise
	# call the CLI main function and return its exit code
	return _cli.main(argv)


__all__ = [
    "functions",
    "render_string",
    "render_template_obj",
    "load_and_render_yaml",
    "main_cli",
    "load_addon",
    "load_addons",
	"load_addons_from_dir",
	"load_and_render_file",
	"teardown_addons",
]

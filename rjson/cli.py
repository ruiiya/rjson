import argparse
import json
import yaml
from .helpers import functions
from template_runtime import TemplateRuntime


def _build_cli():
    p = argparse.ArgumentParser(prog="rjson", description="Render template YAML or run demo")
    p.add_argument("--file", "-f", help="YAML template file to render")
    p.add_argument("--seed", "-s", type=int, help="Optional random seed to make output deterministic")
    p.add_argument("--demo", action="store_true", help="Run built-in demo template")
    p.add_argument("--out", "-o", help="Write output JSON to file instead of stdout")
    p.add_argument("--addon", "-a", action="append", help="Path to a Python addon file that provides extra functions. Can be repeated.")
    p.add_argument("--addon-dir", help="Directory containing Python addon files to load (all .py files will be loaded)")
    return p


def render_template_obj(obj, context=None):
    rt = TemplateRuntime(context or {}, functions)
    return rt.render(obj)


def load_and_render_yaml(path, context=None):
    with open(path, "r", encoding="utf-8") as f:
        tpl = yaml.safe_load(f)
    return render_template_obj(tpl, context=context)


def main(argv=None):
    parser = _build_cli()
    args = parser.parse_args(argv)
    if args.seed is not None:
        import random
        random.seed(args.seed)

    # Load addons if provided
    if getattr(args, "addon", None):
        from .helpers import load_addons
        load_results = load_addons(args.addon)
        for p, res in load_results.items():
            if isinstance(res, str) and res.startswith("ERROR"):
                print(f"Failed to load addon {p}: {res}")
            else:
                print(f"Loaded addon {p}: {res}")
    # Load addons from directory
    if getattr(args, "addon_dir", None):
        from .helpers import load_addons_from_dir
        dir_results = load_addons_from_dir(args.addon_dir)
        for p, res in dir_results.items():
            if isinstance(res, str) and res.startswith("ERROR"):
                print(f"Failed to load addon {p}: {res}")
            else:
                print(f"Loaded addon {p}: {res}")

    # demo: built-in minimal example
    if args.demo:
        # Auto-load example addons if available, then render demo that uses addons when present.
        imported = False
        try:
            import os
            example_dir = os.path.join(os.getcwd(), 'examples', 'addons')
            if os.path.isdir(example_dir):
                from .helpers import load_addons_from_dir
                load_results = load_addons_from_dir(example_dir)
                for p, res in load_results.items():
                    if isinstance(res, str) and res.startswith('ERROR'):
                        print(f'Failed to load addon {p}: {res}')
                    else:
                        print(f'Loaded addon {p}: {res}')
                imported = True
        except Exception:
            # ignore addon load failures for demo
            imported = False

        # If addons added useful functions, try an addon-powered demo; otherwise a static message.
        demo_tpl = {"greeting": "Hello from rjson"}
        # try to use $shout if available
        if 'shout' in functions:
            demo_tpl = {"greeting": "$shout('hello demo')"}
        elif 'repeat' in functions:
            demo_tpl = {"greeting": "$repeat('x', 5)"}

        try:
            res = render_template_obj(demo_tpl)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except Exception as e:
            # fallback to static message
            print(json.dumps({"greeting": "Hello from rjson"}, indent=2, ensure_ascii=False))
        return 0

    if args.file:
        # supports YAML and JSON
        from . import load_and_render_file
        res = load_and_render_file(args.file)
        out_json = json.dumps(res, indent=2, ensure_ascii=False)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(out_json)
            print(f"Wrote output to {args.out}")
        else:
            print(out_json)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    main()

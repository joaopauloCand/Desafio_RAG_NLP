from pathlib import Path
import runpy

# Backward-compatible entrypoint: keeps `python setup.py` and `import setup` working.
_MODULE_PATH = Path(__file__).resolve().parent / "setup" / "setup.py"
_MODULE_GLOBALS = runpy.run_path(str(_MODULE_PATH))

globals().update(
    {
        k: v
        for k, v in _MODULE_GLOBALS.items()
        if not (k.startswith("__") and k.endswith("__"))
    }
)

if __name__ == "__main__":
    _MODULE_GLOBALS["main"]()

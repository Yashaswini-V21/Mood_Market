# c:\Mood_Market\celery\__init__.py
import sys
import os

# To prevent local celery/ directory shadowing the third-party 'celery' library:
# We temporarily exclude parent directories from sys.path, import the real celery,
# and redirect the module cache.
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
saved_path = list(sys.path)
saved_module = sys.modules.pop("celery", None)

try:
    sys.path = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) != os.path.normcase(parent_dir) and p not in ("", ".")]
    import celery as _real_celery
    # Expose standard celery attributes in this package and extend path search for submodules
    if hasattr(_real_celery, "__path__"):
        local_path = os.path.abspath(os.path.dirname(__file__))
        if local_path not in _real_celery.__path__:
            _real_celery.__path__.append(local_path)
    globals().update(_real_celery.__dict__)
    # Override sys.modules to point to the official library
    sys.modules["celery"] = _real_celery
except Exception as e:
    if saved_module is not None:
        sys.modules["celery"] = saved_module
    raise e
finally:
    sys.path = saved_path

# clean architecture alignment

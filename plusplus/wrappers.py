import importlib
import sys
from types import FunctionType

from plusplus.patching import patch_code


patched_packages = set()


def enable_increments(where):
    if isinstance(where, str):
        PatchingFinder.register_import_path(where)
        return

    if isinstance(where, FunctionType):
        where.__code__ = patch_code(where.__code__)
        return where

    if isinstance(where, type):
        raise TypeError(
            "Decorating classes is not supported. Please enable_increments() in the whole package "
            "or define the class inside a function decorated with @enable_increments instead")
    raise TypeError('Unexpected argument {} of type {}'.format(repr(where), type(where)))


class PatchingFinder(importlib.abc.MetaPathFinder):
    _patched_import_paths = set()

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        if not cls._is_patching_needed(fullname):
            return None

        for finder in sys.meta_path:
            if finder is cls:
                continue

            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                spec.loader = PatchingLoader(spec.loader)
                return spec
        return None

    @classmethod
    def _is_patching_needed(cls, import_path):
        import_path = import_path.split('.')
        return any('.'.join(import_path[:i]) in cls._patched_import_paths
                   for i in range(len(import_path) + 1))

    @classmethod
    def register_import_path(cls, import_path):
        if not cls._patched_import_paths:
            sys.meta_path.insert(0, cls)

        cls._patched_import_paths.add(import_path)


class PatchingLoader(importlib.abc.InspectLoader):
    def __init__(self, wrapped_loader):
        self._wrapped_loader = wrapped_loader

    def get_code(self, fullname):
        return patch_code(self._wrapped_loader.get_code(fullname))

    def get_source(self, fullname):
        return self._wrapped_loader.get_source(fullname)

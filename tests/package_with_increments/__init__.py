# This enables increments for the whole package (no need to write @enable_increments)
# besides this file. Should be called before any subpackage is imported.

from plusplus import enable_increments
enable_increments(__name__)

from package_with_increments.module import CONSTANT, increment_and_return


__all__ = ['CONSTANT', 'increment_and_return']

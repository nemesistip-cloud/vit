"""API route package.

Route modules are imported explicitly by the application bootstrap. Keeping
this package lazy prevents an optional integration failure from unmounting
unrelated routes such as authentication and administration.
"""

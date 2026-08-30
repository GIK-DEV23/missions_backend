"""
Main authentication module for handling user authentication across the system.

Deliberately no eager re-exports here (see CHANGES.md ticket 10) — this
package's models.py now makes it a real installed app, and eagerly
importing authentication.backends/.utils/.middleware at package-import
time (which themselves import users.models) broke Django's app-loading
before the registry was ready. Nothing outside this package used these
re-exports (verified — only authentication.permissions_list and
authentication.schemas are imported elsewhere, as actual submodule
imports), so removing them is safe. Import from the specific submodule
instead, e.g. `from authentication.backends import get_backend`.
"""
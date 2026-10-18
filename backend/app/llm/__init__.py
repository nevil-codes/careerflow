"""LLM provider layer.

Providers only ever *read* the profile (see ``context.py``); writes to the profile
tables are blocked outside the seed by the guard in ``app.models``.
"""

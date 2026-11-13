"""The Provider Gateway (ROUNDS-14-L02; DR-0002 decision D8).

The only package that opens a saved AI provider key. ``keyring`` derives
every key the runner makes from ``AI_KEY_SECRET``; ``custody`` reads and
writes saved provider keys and model lists through PocketBase's hook routes.
"""

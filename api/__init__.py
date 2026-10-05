"""Cafe Finder read API.

Thin HTTP adapter over the existing ``cafe_finder`` domain modules.
All business logic (search, distance, ranking, quality, analytics)
lives in ``src/cafe_finder/``; this package only handles HTTP transport,
query validation, and JSON serialization.
"""

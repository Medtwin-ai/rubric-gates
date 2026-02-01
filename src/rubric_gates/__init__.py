"""
PATH: src/rubric_gates/__init__.py
PURPOSE: Public Rubric Gates package entrypoint.

WHY: Keep the verifier + schema utilities in a small, importable library that can be
     used by the public harness and by the private service (without exposing agents).

DEPENDENCIES:
- jsonschema
- PyYAML
"""

__all__ = ["__version__"]

__version__ = "0.1.0"


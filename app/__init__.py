"""CreditNexus: FINOS-Compliant Financial AI Agent"""

# Passlib's bcrypt handler expects bcrypt.__about__.__version__ (removed in bcrypt 4.1+).
# Shim so passlib can load without AttributeError.
try:
    import bcrypt as _bcrypt
    if not hasattr(_bcrypt, "__about__"):
        import types
        _bcrypt.__about__ = types.SimpleNamespace(
            __version__=getattr(_bcrypt, "__version__", "4.1.0")
        )
except Exception:
    pass

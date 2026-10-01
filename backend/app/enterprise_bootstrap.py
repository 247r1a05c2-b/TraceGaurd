from .performance import ensure_indexes


def bootstrap_enterprise_storage() -> None:
    try:
        ensure_indexes()
    except Exception:
        # Readiness will expose a database failure; the API remains bootable while the database recovers.
        pass

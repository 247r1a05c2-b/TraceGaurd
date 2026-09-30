from pathlib import Path


def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f'Patch anchor not found: {path}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

replace_once(
    'backend/app/monitoring.py',
    '\ndef record_audit(event: str, actor: str, details: dict[str, Any]) -> None:',
    '\n\ndef remove_client(client_id: str) -> dict[str, Any]:\n    if client_id not in clients:\n        raise KeyError(client_id)\n    return clients.pop(client_id)\n\n\ndef record_audit(event: str, actor: str, details: dict[str, Any]) -> None:'
)
replace_once(
    'backend/app/main.py',
    'from .monitoring import audit_log, clients, execute_approved_action, execution_log, heartbeat, check_website, hydrate_clients, record_audit, register_client',
    'from .monitoring import audit_log, clients, execute_approved_action, execution_log, heartbeat, check_website, hydrate_clients, record_audit, register_client, remove_client'
)
replace_once(
    'backend/app/main.py',
    '\n\n@app.post("/api/v1/clients/{client_id}/heartbeat")',
    '\n\n@app.delete("/api/v1/clients/{client_id}")\ndef delete_client(client_id: str, engineer: str = Depends(current_engineer)):\n    try:\n        client = remove_client(client_id)\n    except KeyError as exc:\n        raise HTTPException(status_code=404, detail="Client not found") from exc\n    with SessionLocal() as session:\n        record = session.get(ClientRecord, client_id)\n        if record is not None:\n            session.delete(record)\n            session.commit()\n    record_audit("CLIENT_REMOVED", engineer, {"client_id": client_id, "name": client.get("name")})\n    return {"removed": True, "client_id": client_id, "name": client.get("name"), "message": "Client removed from active monitoring. Historical incidents are preserved."}\n\n\n@app.post("/api/v1/clients/{client_id}/heartbeat")'
)

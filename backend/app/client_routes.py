from fastapi import Depends, HTTPException

from .database import ClientRecord, SessionLocal
from .main import current_engineer
from .monitoring import clients, record_audit


def install_client_routes(app):
    @app.delete('/api/v1/clients/{client_id}')
    def delete_client(client_id: str, engineer: str = Depends(current_engineer)):
        client = clients.pop(client_id, None)
        if client is None:
            raise HTTPException(status_code=404, detail='Client not found')
        with SessionLocal() as session:
            record = session.get(ClientRecord, client_id)
            if record is not None:
                session.delete(record)
                session.commit()
        record_audit('CLIENT_REMOVED', engineer, {'client_id': client_id, 'name': client.get('name')})
        return {
            'removed': True,
            'client_id': client_id,
            'name': client.get('name'),
            'message': 'Client removed from active monitoring. Historical incidents are preserved.'
        }

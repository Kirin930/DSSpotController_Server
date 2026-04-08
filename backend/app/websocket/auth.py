from __future__ import annotations

from sqlalchemy.orm import Session

from ..schemas.websocket import HelloPayload
from ..services.node_service import NodeService


def authenticate_node(db: Session, node_service: NodeService, payload: HelloPayload):
    return node_service.handle_hello(db, payload)

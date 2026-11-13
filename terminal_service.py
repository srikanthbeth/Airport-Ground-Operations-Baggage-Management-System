from sqlalchemy import select
from sqlalchemy.orm import Session

from models.airport import Airport
from models.terminal import Terminal
from schemas.terminal import TerminalCreate, TerminalUpdate
from core.constants import TerminalStatus

def create_terminal(db: Session, data: TerminalCreate):
    airport = db.get(Airport, data.airport_id)

    if not airport or not airport.is_active:
        return None

    existing = db.scalar(
        select(Terminal).where(
            Terminal.airport_id == data.airport_id,
            Terminal.code == data.code,
        )
    )
    if existing:
        return False

    terminal = Terminal(**data.model_dump())
    db.add(terminal)
    db.commit()
    db.refresh(terminal)
    return terminal


def get_terminal(db: Session, terminal_id):
    return db.get(Terminal, terminal_id)


def list_terminals(
    db: Session, airport_id, skip: int = 0, limit: int = 100
):
    return db.scalars(
        select(Terminal)
        .where(Terminal.airport_id == airport_id)
        .order_by(Terminal.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()


def update_terminal(db: Session, terminal: Terminal, data: TerminalUpdate):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(terminal, field, value)

    db.commit()
    db.refresh(terminal)
    return terminal


def deactivate_terminal(db: Session, terminal: Terminal):
    terminal.status = TerminalStatus.INACTIVE
    db.commit()
    db.refresh(terminal)
    return terminal
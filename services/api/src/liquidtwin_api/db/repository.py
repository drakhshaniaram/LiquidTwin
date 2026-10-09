from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from liquidtwin_api.db.models import Terminal, TerminalVersion


class TerminalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_terminals(self) -> list[Terminal]:
        return list(self.session.scalars(select(Terminal).order_by(Terminal.name)))

    def get_terminal(self, terminal_id: UUID) -> Terminal | None:
        return self.session.get(Terminal, terminal_id)

    def list_versions(self, terminal_id: UUID) -> list[TerminalVersion]:
        return list(
            self.session.scalars(
                select(TerminalVersion)
                .where(TerminalVersion.terminal_id == terminal_id)
                .order_by(TerminalVersion.version.desc())
            )
        )

    def delete_terminal(self, terminal_id: UUID) -> bool:
        terminal = self.get_terminal(terminal_id)
        if terminal is None:
            return False
        self.session.delete(terminal)
        self.session.flush()
        return True

    def create_terminal(
        self,
        name: str,
        document: dict[str, Any],
        note: str | None = None,
    ) -> Terminal:
        terminal = Terminal(name=name, current_version=1)
        self.session.add(terminal)
        self.session.flush()
        self.session.add(
            TerminalVersion(
                terminal_id=terminal.id,
                version=1,
                document=document,
                note=note,
            )
        )
        self.session.flush()
        return terminal

    def load_document(self, terminal_id: UUID, version: int | None = None) -> dict[str, Any] | None:
        terminal = self.session.get(Terminal, terminal_id)
        if terminal is None:
            return None

        version_number = terminal.current_version if version is None else version
        record = self.session.get(TerminalVersion, (terminal_id, version_number))
        return None if record is None else record.document

    def append_version(
        self,
        terminal_id: UUID,
        document: dict[str, Any],
        note: str | None = None,
    ) -> TerminalVersion | None:
        terminal = self.session.scalar(
            select(Terminal).where(Terminal.id == terminal_id).with_for_update()
        )
        if terminal is None:
            return None

        version = terminal.current_version + 1
        record = TerminalVersion(
            terminal_id=terminal_id,
            version=version,
            document=document,
            note=note,
        )
        terminal.current_version = version
        self.session.add(record)
        self.session.flush()
        return record
"""One router per resource. Dependencies shared by the resource routers."""

from collections.abc import Iterator
from typing import Annotated
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from ..clock import Clock, get_clock
from ..settings import Settings

def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessionmaker() as session:
        yield session

def get_settings(request: Request) -> Settings:
    return request.app.state.settings

SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

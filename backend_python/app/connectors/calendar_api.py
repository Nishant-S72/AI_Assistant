"""Abstract calendar provider interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class CalendarEvent:
    """Calendar event data structure."""
    external_id: str
    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    attendees: List[Dict[str, str]] = None
    recurrence_rule: Optional[str] = None
    status: str = "confirmed"
    calendar_id: Optional[str] = None
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []


@dataclass
class FreeBusySlot:
    """Free/busy time slot."""
    start: datetime
    end: datetime
    busy: bool


class CalendarProvider(ABC):
    """Abstract interface for calendar providers."""
    
    @abstractmethod
    async def list_events(
        self,
        calendar_id: str,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
    ) -> List[CalendarEvent]:
        """List events in a calendar."""
        pass
    
    @abstractmethod
    async def create_event(
        self,
        calendar_id: str,
        event: CalendarEvent,
    ) -> CalendarEvent:
        """Create a new event."""
        pass
    
    @abstractmethod
    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: CalendarEvent,
    ) -> CalendarEvent:
        """Update an existing event."""
        pass
    
    @abstractmethod
    async def delete_event(
        self,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        """Delete an event."""
        pass
    
    @abstractmethod
    async def get_freebusy(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> List[FreeBusySlot]:
        """Get free/busy information."""
        pass
    
    @abstractmethod
    async def refresh_token(self) -> bool:
        """Refresh OAuth token if expired."""
        pass



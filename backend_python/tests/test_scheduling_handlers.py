"""Unit tests for scheduling handlers."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.tools.scheduling_handlers import (
    parse_schedule,
    create_event,
    find_availability,
    reschedule_event,
    cancel_event,
    create_reminder,
)


@pytest.mark.asyncio
async def test_parse_schedule():
    """Test parsing natural language schedule."""
    result = await parse_schedule("Schedule a meeting tomorrow at 2pm with John")
    
    assert "title" in result
    assert "start_time" in result
    assert "end_time" in result


@pytest.mark.asyncio
async def test_create_event():
    """Test creating an event."""
    with patch('app.tools.scheduling_handlers.get_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock calendar connection
        mock_conn.fetchrow.return_value = {
            "id": "conn-1",
            "calendar_id": "primary",
            "access_token": "token",
            "refresh_token": "refresh",
        }
        
        # Mock adapter
        with patch('app.tools.scheduling_handlers.GoogleCalendarAdapter') as mock_adapter:
            mock_adapter_instance = AsyncMock()
            mock_adapter.return_value = mock_adapter_instance
            mock_adapter_instance.create_event.return_value = MagicMock(
                external_id="event-123",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                attendees=[],
            )
            
            # Mock execute
            mock_conn.execute = AsyncMock()
            
            result = await create_event(
                title="Test Meeting",
                start_time=(datetime.now() + timedelta(days=1)).isoformat(),
                end_time=(datetime.now() + timedelta(days=1, hours=1)).isoformat(),
                user_id="user-1",
            )
            
            assert result["success"] is True
            assert "event_id" in result


@pytest.mark.asyncio
async def test_find_availability():
    """Test finding availability."""
    with patch('app.tools.scheduling_handlers.get_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_conn.fetchrow.return_value = {
            "id": "conn-1",
            "calendar_id": "primary",
            "access_token": "token",
        }
        
        with patch('app.tools.scheduling_handlers.GoogleCalendarAdapter') as mock_adapter:
            mock_adapter_instance = AsyncMock()
            mock_adapter.return_value = mock_adapter_instance
            mock_adapter_instance.get_freebusy.return_value = []
            
            result = await find_availability(
                user_id="user-1",
                start_date=datetime.now().isoformat(),
                end_date=(datetime.now() + timedelta(days=7)).isoformat(),
            )
            
            assert "available_slots" in result


@pytest.mark.asyncio
async def test_reschedule_event():
    """Test rescheduling an event."""
    with patch('app.tools.scheduling_handlers.get_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_conn.fetchrow.side_effect = [
            {
                "external_event_id": "ext-123",
                "calendar_provider": "google",
                "calendar_id": "primary",
            },
            {
                "access_token": "token",
                "refresh_token": "refresh",
            },
        ]
        
        with patch('app.tools.scheduling_handlers.GoogleCalendarAdapter') as mock_adapter:
            mock_adapter_instance = AsyncMock()
            mock_adapter.return_value = mock_adapter_instance
            mock_adapter_instance.update_event = AsyncMock()
            mock_conn.execute = AsyncMock()
            
            result = await reschedule_event(
                event_id="event-1",
                new_start_time=(datetime.now() + timedelta(days=2)).isoformat(),
                new_end_time=(datetime.now() + timedelta(days=2, hours=1)).isoformat(),
                user_id="user-1",
            )
            
            assert result["success"] is True


@pytest.mark.asyncio
async def test_cancel_event():
    """Test cancelling an event."""
    with patch('app.tools.scheduling_handlers.get_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_conn.fetchrow.side_effect = [
            {
                "external_event_id": "ext-123",
                "calendar_provider": "google",
                "calendar_id": "primary",
            },
            {
                "access_token": "token",
            },
        ]
        
        with patch('app.tools.scheduling_handlers.GoogleCalendarAdapter') as mock_adapter:
            mock_adapter_instance = AsyncMock()
            mock_adapter.return_value = mock_adapter_instance
            mock_adapter_instance.delete_event = AsyncMock(return_value=True)
            mock_conn.execute = AsyncMock()
            
            result = await cancel_event(
                event_id="event-1",
                user_id="user-1",
            )
            
            assert result["success"] is True


@pytest.mark.asyncio
async def test_create_reminder():
    """Test creating a reminder."""
    with patch('app.tools.scheduling_handlers.get_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
        
        mock_conn.fetchrow.return_value = {
            "start_time": datetime.now() + timedelta(days=1),
        }
        
        mock_conn.execute = AsyncMock()
        
        with patch('app.tools.scheduling_handlers.schedule_reminder') as mock_schedule:
            mock_schedule.return_value = "job-123"
            
            result = await create_reminder(
                event_id="event-1",
                user_id="user-1",
                reminder_type="email",
                minutes_before=15,
            )
            
            assert result["success"] is True
            assert "reminder_id" in result



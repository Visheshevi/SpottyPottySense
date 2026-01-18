"""
Pydantic Data Validation Models for SpottyPottySense.

This module defines comprehensive Pydantic models for all data entities
in the application, providing:
- Automatic data validation
- Type safety
- Serialization/deserialization
- Documentation through type hints
- Custom validators for business logic

Models:
    - Sensor: Motion sensor configuration
    - User: User profile and preferences
    - Session: Playback session tracking
    - MotionEvent: Individual motion detection event
    - Spotify configuration objects
    - API request/response models

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

from datetime import datetime, time
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import (
    BaseModel,
    Field,
    validator,
    root_validator,
    EmailStr,
    HttpUrl,
    constr,
    conint,
    confloat
)


# ==============================================================================
# ENUMERATIONS
# ==============================================================================

class SensorStatus(str, Enum):
    """Sensor operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


class SessionStatus(str, Enum):
    """Session playback status."""
    ACTIVE = "active"
    ENDED = "ended"
    TIMEOUT = "timeout"
    MANUAL_STOP = "manual_stop"


class MotionEventType(str, Enum):
    """Types of motion events."""
    MOTION_DETECTED = "motion_detected"
    MOTION_CLEARED = "motion_cleared"
    HEARTBEAT = "heartbeat"


class SpotifyPlaybackState(str, Enum):
    """Spotify playback states."""
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


# ==============================================================================
# BASE MODEL
# ==============================================================================

class SpottyPottySenseBaseModel(BaseModel):
    """
    Base model with common configuration for all Pydantic models.
    """
    
    class Config:
        # Allow arbitrary types (for datetime, etc.)
        arbitrary_types_allowed = True
        # Use enum values instead of enum objects
        use_enum_values = True
        # Validate on assignment
        validate_assignment = True
        # Extra fields forbidden
        extra = "forbid"
        # JSON encoders for custom types
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            time: lambda v: v.isoformat(),
        }


# ==============================================================================
# QUIET HOURS CONFIGURATION
# ==============================================================================

class QuietHours(SpottyPottySenseBaseModel):
    """
    Configuration for quiet hours when playback should not start.
    
    Attributes:
        enabled: Whether quiet hours are enabled
        start_time: Start time (HH:MM format, 24-hour)
        end_time: End time (HH:MM format, 24-hour)
        days: Days of week when active (0=Monday, 6=Sunday)
    """
    
    enabled: bool = Field(False, description="Whether quiet hours are enabled")
    start_time: Optional[str] = Field(
        None,
        regex=r"^([01]\d|2[0-3]):([0-5]\d)$",
        description="Start time in HH:MM format (24-hour)",
        example="22:00"
    )
    end_time: Optional[str] = Field(
        None,
        regex=r"^([01]\d|2[0-3]):([0-5]\d)$",
        description="End time in HH:MM format (24-hour)",
        example="07:00"
    )
    days: List[int] = Field(
        default_factory=lambda: list(range(7)),
        description="Days of week (0=Monday, 6=Sunday)",
        min_items=0,
        max_items=7
    )
    
    @validator('days')
    def validate_days(cls, v):
        """Validate days are in range 0-6."""
        if not all(0 <= day <= 6 for day in v):
            raise ValueError("Days must be between 0 (Monday) and 6 (Sunday)")
        return sorted(set(v))  # Remove duplicates and sort
    
    @root_validator
    def validate_times(cls, values):
        """Validate that times are provided when enabled."""
        if values.get('enabled'):
            if not values.get('start_time') or not values.get('end_time'):
                raise ValueError("start_time and end_time required when enabled=True")
        return values


# ==============================================================================
# SPOTIFY CONFIGURATION
# ==============================================================================

class SpotifyPlaybackConfig(SpottyPottySenseBaseModel):
    """
    Spotify playback configuration.
    
    Attributes:
        device_id: Spotify device ID to play on
        playlist_uri: Spotify playlist URI
        shuffle: Whether to shuffle playback
        volume_percent: Initial volume (0-100)
        context_uri: Optional context URI (album, artist, playlist)
    """
    
    device_id: Optional[str] = Field(None, description="Spotify device ID")
    playlist_uri: Optional[str] = Field(
        None,
        regex=r"^spotify:(playlist|album|artist):[a-zA-Z0-9]+$",
        description="Spotify playlist/album/artist URI",
        example="spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
    )
    shuffle: bool = Field(True, description="Enable shuffle mode")
    volume_percent: Optional[conint(ge=0, le=100)] = Field(
        None,
        description="Volume level (0-100)"
    )
    context_uri: Optional[str] = Field(
        None,
        description="Context URI for playback"
    )


# ==============================================================================
# SENSOR MODEL
# ==============================================================================

class Sensor(SpottyPottySenseBaseModel):
    """
    Motion sensor configuration and state.
    
    Represents a physical IoT sensor device that detects motion
    and triggers Spotify playback.
    """
    
    # Primary key
    sensor_id: constr(min_length=1, max_length=128, regex=r"^[a-zA-Z0-9_-]+$") = Field(
        ...,
        description="Unique sensor identifier",
        example="sensor-bathroom-001"
    )
    
    # Foreign key
    user_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="User ID who owns this sensor"
    )
    
    # Basic info
    name: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Human-readable sensor name",
        example="Bathroom Motion Sensor"
    )
    location: constr(min_length=1, max_length=256) = Field(
        ...,
        description="Physical location of sensor",
        example="Main Bathroom"
    )
    description: Optional[constr(max_length=512)] = Field(
        None,
        description="Optional description"
    )
    
    # Status
    status: SensorStatus = Field(
        SensorStatus.ACTIVE,
        description="Current sensor status"
    )
    
    # Configuration
    enabled: bool = Field(True, description="Whether sensor is enabled")
    motion_debounce_minutes: conint(ge=1, le=60) = Field(
        2,
        description="Minutes to wait before triggering again after motion",
        example=2
    )
    timeout_minutes: conint(ge=1, le=120) = Field(
        5,
        description="Minutes of no motion before stopping playback",
        example=5
    )
    
    # Spotify configuration
    spotify_config: SpotifyPlaybackConfig = Field(
        default_factory=SpotifyPlaybackConfig,
        description="Spotify playback configuration"
    )
    
    # Quiet hours
    quiet_hours: QuietHours = Field(
        default_factory=QuietHours,
        description="Quiet hours configuration"
    )
    
    # Timestamps
    last_motion_time: Optional[datetime] = Field(
        None,
        description="Timestamp of last detected motion"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    # IoT device info
    device_certificate_id: Optional[str] = Field(
        None,
        description="AWS IoT device certificate ID"
    )
    firmware_version: Optional[str] = Field(
        None,
        description="Sensor firmware version",
        example="1.2.3"
    )
    last_seen: Optional[datetime] = Field(
        None,
        description="Last communication from sensor"
    )
    
    @validator('updated_at', always=True)
    def set_updated_at(cls, v):
        """Always update the updated_at timestamp."""
        return datetime.utcnow()


# ==============================================================================
# USER MODEL
# ==============================================================================

class UserPreferences(SpottyPottySenseBaseModel):
    """User preference settings."""
    
    notifications_enabled: bool = Field(True, description="Enable notifications")
    email_notifications: bool = Field(False, description="Email notifications")
    default_volume: Optional[conint(ge=0, le=100)] = Field(
        50,
        description="Default volume level"
    )
    theme: str = Field("light", description="UI theme preference")


class SpotifyTokens(SpottyPottySenseBaseModel):
    """Spotify OAuth tokens (stored in Secrets Manager, not DynamoDB)."""
    
    access_token: str = Field(..., description="Spotify access token")
    refresh_token: str = Field(..., description="Spotify refresh token")
    expires_at: datetime = Field(..., description="Token expiration time")
    scope: str = Field(..., description="OAuth scopes")


class User(SpottyPottySenseBaseModel):
    """
    User profile and configuration.
    
    Represents a SpottyPottySense user with Spotify integration.
    """
    
    # Primary key
    user_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Unique user identifier (Cognito sub)",
        example="auth0|123456789"
    )
    
    # Profile
    email: EmailStr = Field(..., description="User email address")
    name: constr(min_length=1, max_length=128) = Field(
        ...,
        description="User's full name"
    )
    
    # Spotify integration
    spotify_user_id: Optional[str] = Field(
        None,
        description="Spotify user ID"
    )
    spotify_connected: bool = Field(
        False,
        description="Whether Spotify account is connected"
    )
    spotify_token_secret_arn: Optional[str] = Field(
        None,
        description="ARN of secret containing Spotify tokens"
    )
    
    # Preferences
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
        description="User preferences"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    last_login: Optional[datetime] = Field(
        None,
        description="Last login timestamp"
    )
    
    # Status
    active: bool = Field(True, description="Whether account is active")
    
    @validator('updated_at', always=True)
    def set_updated_at(cls, v):
        """Always update the updated_at timestamp."""
        return datetime.utcnow()


# ==============================================================================
# SESSION MODEL
# ==============================================================================

class Session(SpottyPottySenseBaseModel):
    """
    Playback session tracking.
    
    Represents a single playback session triggered by motion detection.
    """
    
    # Primary key
    session_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Unique session identifier",
        example="session-20260117-123456-abc"
    )
    
    # Foreign keys
    user_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="User ID"
    )
    sensor_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Sensor ID that triggered session"
    )
    
    # Session info
    status: SessionStatus = Field(
        SessionStatus.ACTIVE,
        description="Current session status"
    )
    
    # Timestamps
    start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session start time"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="Session end time"
    )
    last_motion_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last motion detected in this session"
    )
    
    # Spotify playback info
    spotify_device_id: Optional[str] = Field(
        None,
        description="Spotify device used for playback"
    )
    spotify_context_uri: Optional[str] = Field(
        None,
        description="Spotify context (playlist/album) played"
    )
    playback_started: bool = Field(
        False,
        description="Whether playback actually started"
    )
    
    # Statistics
    motion_events_count: conint(ge=0) = Field(
        0,
        description="Number of motion events in this session"
    )
    duration_minutes: Optional[confloat(ge=0)] = Field(
        None,
        description="Session duration in minutes"
    )
    
    # TTL for DynamoDB auto-deletion
    ttl: Optional[int] = Field(
        None,
        description="Unix timestamp for DynamoDB TTL"
    )
    
    @validator('duration_minutes', always=True)
    def calculate_duration(cls, v, values):
        """Calculate duration if end_time is set."""
        if values.get('end_time') and values.get('start_time'):
            delta = values['end_time'] - values['start_time']
            return round(delta.total_seconds() / 60, 2)
        return v


# ==============================================================================
# MOTION EVENT MODEL
# ==============================================================================

class MotionEvent(SpottyPottySenseBaseModel):
    """
    Individual motion detection event.
    
    Records each motion event from a sensor for analytics and debugging.
    """
    
    # Primary key (composite: sensorId + timestamp)
    event_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Unique event identifier",
        example="event-sensor001-20260117-123456"
    )
    
    # Foreign keys
    sensor_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="Sensor that detected motion"
    )
    user_id: constr(min_length=1, max_length=128) = Field(
        ...,
        description="User ID"
    )
    session_id: Optional[constr(min_length=1, max_length=128)] = Field(
        None,
        description="Associated session ID"
    )
    
    # Event details
    event_type: MotionEventType = Field(
        MotionEventType.MOTION_DETECTED,
        description="Type of motion event"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )
    
    # Action taken
    action_taken: str = Field(
        ...,
        description="Action taken in response to event",
        example="playback_started"
    )
    playback_triggered: bool = Field(
        False,
        description="Whether this event triggered playback"
    )
    
    # Metadata
    firmware_version: Optional[str] = Field(
        None,
        description="Sensor firmware version"
    )
    signal_strength: Optional[confloat(ge=-100, le=0)] = Field(
        None,
        description="WiFi signal strength (dBm)"
    )
    battery_level: Optional[conint(ge=0, le=100)] = Field(
        None,
        description="Battery level percentage"
    )
    
    # TTL for DynamoDB auto-deletion
    ttl: Optional[int] = Field(
        None,
        description="Unix timestamp for DynamoDB TTL"
    )


# ==============================================================================
# API REQUEST/RESPONSE MODELS
# ==============================================================================

class CreateSensorRequest(SpottyPottySenseBaseModel):
    """API request to create a new sensor."""
    
    sensor_id: constr(min_length=1, max_length=128, regex=r"^[a-zA-Z0-9_-]+$")
    name: constr(min_length=1, max_length=128)
    location: constr(min_length=1, max_length=256)
    description: Optional[constr(max_length=512)] = None
    motion_debounce_minutes: Optional[conint(ge=1, le=60)] = 2
    timeout_minutes: Optional[conint(ge=1, le=120)] = 5
    spotify_config: Optional[SpotifyPlaybackConfig] = None
    quiet_hours: Optional[QuietHours] = None


class UpdateSensorRequest(SpottyPottySenseBaseModel):
    """API request to update sensor configuration."""
    
    name: Optional[constr(min_length=1, max_length=128)] = None
    location: Optional[constr(min_length=1, max_length=256)] = None
    description: Optional[constr(max_length=512)] = None
    status: Optional[SensorStatus] = None
    enabled: Optional[bool] = None
    motion_debounce_minutes: Optional[conint(ge=1, le=60)] = None
    timeout_minutes: Optional[conint(ge=1, le=120)] = None
    spotify_config: Optional[SpotifyPlaybackConfig] = None
    quiet_hours: Optional[QuietHours] = None


class UpdateUserRequest(SpottyPottySenseBaseModel):
    """API request to update user profile."""
    
    name: Optional[constr(min_length=1, max_length=128)] = None
    preferences: Optional[UserPreferences] = None


class ApiResponse(SpottyPottySenseBaseModel):
    """Standard API response wrapper."""
    
    success: bool = Field(..., description="Whether request succeeded")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")


class PaginatedResponse(SpottyPottySenseBaseModel):
    """Paginated API response."""
    
    items: List[Dict[str, Any]] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def validate_sensor_data(data: Dict[str, Any]) -> Sensor:
    """
    Validate and parse sensor data.
    
    Args:
        data: Raw sensor data dictionary
        
    Returns:
        Validated Sensor instance
        
    Raises:
        ValidationError: If validation fails
    """
    return Sensor(**data)


def validate_user_data(data: Dict[str, Any]) -> User:
    """
    Validate and parse user data.
    
    Args:
        data: Raw user data dictionary
        
    Returns:
        Validated User instance
        
    Raises:
        ValidationError: If validation fails
    """
    return User(**data)


def validate_session_data(data: Dict[str, Any]) -> Session:
    """
    Validate and parse session data.
    
    Args:
        data: Raw session data dictionary
        
    Returns:
        Validated Session instance
        
    Raises:
        ValidationError: If validation fails
    """
    return Session(**data)


def validate_motion_event_data(data: Dict[str, Any]) -> MotionEvent:
    """
    Validate and parse motion event data.
    
    Args:
        data: Raw motion event data dictionary
        
    Returns:
        Validated MotionEvent instance
        
    Raises:
        ValidationError: If validation fails
    """
    return MotionEvent(**data)

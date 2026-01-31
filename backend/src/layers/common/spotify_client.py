"""
Spotify Web API Client with Advanced Features.

This module provides a comprehensive Spotify API client with:
- OAuth token refresh with automatic retry
- Playback control (start, pause, skip, volume)
- Device management
- Playlist and track operations
- Rate limit handling with exponential backoff
- Comprehensive error handling
- Request/response logging for debugging

The Spotify Web API documentation: https://developer.spotify.com/documentation/web-api

Usage:
    from spotify_client import SpotifyClient
    
    # Initialize with access token
    client = SpotifyClient(access_token="your_token")
    
    # Start playback
    client.start_playback(
        device_id="device_id",
        playlist_uri="spotify:playlist:123",
        shuffle=True
    )
    
    # Get available devices
    devices = client.get_devices()

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from base64 import b64encode
import requests
from requests.adapters import HTTPAdapter, Retry

from exceptions import (
    SpotifyAPIError,
    SpotifyAuthenticationError,
    SpotifyRateLimitError,
    SpotifyPlaybackError
)
from logger import get_logger

logger = get_logger(__name__)


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Spotify API base URLs
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_ACCOUNTS_BASE_URL = "https://accounts.spotify.com"

# Retry configuration
MAX_RETRIES = 3
BASE_RETRY_DELAY = 0.5  # 500ms
MAX_RETRY_DELAY = 5.0   # 5 seconds

# Request timeout in seconds
REQUEST_TIMEOUT = 10

# Rate limit safety margin (seconds)
RATE_LIMIT_MARGIN = 1


# ==============================================================================
# SPOTIFY CLIENT CLASS
# ==============================================================================

class SpotifyClient:
    """
    Comprehensive Spotify Web API client.
    
    This class provides methods for interacting with the Spotify Web API:
    - OAuth token management (refresh)
    - Playback control (start, pause, skip, volume, shuffle, repeat)
    - Device management (list, transfer)
    - Playback state queries
    - Rate limit handling with automatic retry
    - Comprehensive error handling
    
    Attributes:
        access_token: Spotify OAuth access token
        session: Requests session with retry configuration
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize Spotify API client.
        
        Args:
            access_token: Spotify OAuth access token
        """
        self.access_token = access_token
        self.session = self._create_session()
        
        logger.info(
            "SpotifyClient initialized",
            extra={"has_token": access_token is not None}
        )
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry configuration.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        
        # Configure automatic retries for network errors
        retry_strategy = Retry(
            total=3,
            status_forcelist=[500, 502, 503, 504],  # Server errors
            backoff_factor=1,
            allowed_methods=["GET", "PUT", "POST", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for Spotify API requests.
        
        Returns:
            Headers dictionary
        """
        if not self.access_token:
            raise SpotifyAuthenticationError("No access token set")
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    # ==========================================================================
    # TOKEN MANAGEMENT
    # ==========================================================================
    
    def refresh_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """
        Refresh Spotify access token using refresh token.
        
        This method exchanges a refresh token for a new access token.
        The new token typically expires in 1 hour.
        
        Args:
            refresh_token: Spotify OAuth refresh token
            client_id: Spotify app client ID
            client_secret: Spotify app client secret
            
        Returns:
            Dictionary with 'access_token', 'expires_in', 'token_type'
            
        Raises:
            SpotifyAuthenticationError: If token refresh fails
            
        Example:
            >>> client = SpotifyClient()
            >>> tokens = client.refresh_token(
            >>>     refresh_token="refresh_token",
            >>>     client_id="client_id",
            >>>     client_secret="client_secret"
            >>> )
            >>> client.access_token = tokens['access_token']
        """
        logger.info("Refreshing Spotify access token")
        
        # Encode client credentials
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            start_time = time.time()
            
            response = self.session.post(
                f"{SPOTIFY_ACCOUNTS_BASE_URL}/api/token",
                headers=headers,
                data=data,
                timeout=REQUEST_TIMEOUT
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Calculate expiration time
                expires_in = token_data.get('expires_in', 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                token_data['expires_at'] = expires_at.isoformat()
                
                logger.info(
                    "Token refreshed successfully",
                    extra={
                        "expires_in": expires_in,
                        "duration_ms": round(duration_ms, 2)
                    }
                )
                
                return token_data
            else:
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error_description', 'Token refresh failed')
                
                logger.error(
                    "Token refresh failed",
                    extra={
                        "status_code": response.status_code,
                        "error": error_data.get('error'),
                        "error_description": error_message
                    }
                )
                
                raise SpotifyAuthenticationError(
                    message=error_message,
                    status_code=response.status_code,
                    response_body=response.text
                )
                
        except requests.RequestException as e:
            logger.error(
                "Token refresh request failed",
                extra={"error": str(e)},
                exc_info=True
            )
            raise SpotifyAuthenticationError(
                message=f"Token refresh request failed: {str(e)}"
            )
    
    # ==========================================================================
    # PLAYBACK CONTROL
    # ==========================================================================
    
    def start_playback(
        self,
        device_id: Optional[str] = None,
        context_uri: Optional[str] = None,
        uris: Optional[List[str]] = None,
        offset: Optional[Dict[str, Any]] = None,
        position_ms: Optional[int] = None,
        shuffle: Optional[bool] = None,
        volume_percent: Optional[int] = None
    ) -> None:
        """
        Start or resume Spotify playback.
        
        Args:
            device_id: Device ID to play on (None = user's active device)
            context_uri: Spotify URI of context (album, artist, playlist)
            uris: List of track URIs to play
            offset: Starting position in context {"position": 0} or {"uri": "spotify:track:..."}
            position_ms: Position in track to start playback (milliseconds)
            shuffle: Enable shuffle mode
            volume_percent: Set volume (0-100)
            
        Raises:
            SpotifyPlaybackError: If playback fails
            
        Example:
            >>> client = SpotifyClient(access_token)
            >>> # Play a playlist
            >>> client.start_playback(
            >>>     device_id="device123",
            >>>     context_uri="spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            >>>     shuffle=True,
            >>>     volume_percent=75
            >>> )
        """
        logger.info(
            "Starting Spotify playback",
            extra={"device_id": device_id, "context_uri": context_uri}
        )
        
        # Build request body
        body = {}
        if context_uri:
            body['context_uri'] = context_uri
        if uris:
            body['uris'] = uris
        if offset:
            body['offset'] = offset
        if position_ms is not None:
            body['position_ms'] = position_ms
        
        # Build query parameters
        params = {}
        if device_id:
            params['device_id'] = device_id
        
        try:
            # Start playback
            self._make_request(
                method="PUT",
                endpoint="/me/player/play",
                params=params,
                json_data=body if body else None,
                expected_status=204
            )
            
            # Set shuffle if requested
            if shuffle is not None:
                time.sleep(0.1)  # Small delay between requests
                self.set_shuffle(shuffle, device_id)
            
            # Set volume if requested
            if volume_percent is not None:
                time.sleep(0.1)
                self.set_volume(volume_percent, device_id)
            
            logger.info("Playback started successfully")
            
        except SpotifyAPIError as e:
            logger.error(
                "Failed to start playback",
                extra={"device_id": device_id, "error": str(e)}
            )
            raise SpotifyPlaybackError(
                message="Failed to start playback",
                device_id=device_id,
                status_code=getattr(e, 'status_code', None)
            )
    
    def pause_playback(self, device_id: Optional[str] = None) -> None:
        """
        Pause Spotify playback.
        
        Args:
            device_id: Device ID (None = user's active device)
            
        Raises:
            SpotifyPlaybackError: If pause fails
        """
        logger.info("Pausing Spotify playback", extra={"device_id": device_id})
        
        params = {}
        if device_id:
            params['device_id'] = device_id
        
        try:
            self._make_request(
                method="PUT",
                endpoint="/me/player/pause",
                params=params,
                expected_status=204
            )
            logger.info("Playback paused successfully")
            
        except SpotifyAPIError as e:
            logger.error("Failed to pause playback", extra={"error": str(e)})
            raise SpotifyPlaybackError(
                message="Failed to pause playback",
                device_id=device_id
            )
    
    def skip_to_next(self, device_id: Optional[str] = None) -> None:
        """Skip to next track."""
        logger.info("Skipping to next track")
        
        params = {}
        if device_id:
            params['device_id'] = device_id
        
        self._make_request(
            method="POST",
            endpoint="/me/player/next",
            params=params,
            expected_status=204
        )
    
    def skip_to_previous(self, device_id: Optional[str] = None) -> None:
        """Skip to previous track."""
        logger.info("Skipping to previous track")
        
        params = {}
        if device_id:
            params['device_id'] = device_id
        
        self._make_request(
            method="POST",
            endpoint="/me/player/previous",
            params=params,
            expected_status=204
        )
    
    def set_volume(self, volume_percent: int, device_id: Optional[str] = None) -> None:
        """
        Set playback volume.
        
        Args:
            volume_percent: Volume level (0-100)
            device_id: Device ID
        """
        if not 0 <= volume_percent <= 100:
            raise ValueError("Volume must be between 0 and 100")
        
        logger.info(f"Setting volume to {volume_percent}%")
        
        params = {'volume_percent': volume_percent}
        if device_id:
            params['device_id'] = device_id
        
        self._make_request(
            method="PUT",
            endpoint="/me/player/volume",
            params=params,
            expected_status=204
        )
    
    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> None:
        """
        Set shuffle mode.
        
        Args:
            state: True to enable shuffle, False to disable
            device_id: Device ID
        """
        logger.info(f"Setting shuffle to {state}")
        
        params = {'state': 'true' if state else 'false'}
        if device_id:
            params['device_id'] = device_id
        
        self._make_request(
            method="PUT",
            endpoint="/me/player/shuffle",
            params=params,
            expected_status=204
        )
    
    def set_repeat(self, state: str, device_id: Optional[str] = None) -> None:
        """
        Set repeat mode.
        
        Args:
            state: 'track', 'context', or 'off'
            device_id: Device ID
        """
        if state not in ['track', 'context', 'off']:
            raise ValueError("State must be 'track', 'context', or 'off'")
        
        logger.info(f"Setting repeat to {state}")
        
        params = {'state': state}
        if device_id:
            params['device_id'] = device_id
        
        self._make_request(
            method="PUT",
            endpoint="/me/player/repeat",
            params=params,
            expected_status=204
        )
    
    # ==========================================================================
    # DEVICE MANAGEMENT
    # ==========================================================================
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get user's available Spotify devices.
        
        Returns:
            List of device dictionaries
            
        Example:
            >>> client = SpotifyClient(access_token)
            >>> devices = client.get_devices()
            >>> for device in devices:
            >>>     print(f"{device['name']} - {device['type']} - Active: {device['is_active']}")
        """
        logger.info("Getting available Spotify devices")
        
        response = self._make_request(
            method="GET",
            endpoint="/me/player/devices"
        )
        
        devices = response.get('devices', [])
        logger.info(
            "Retrieved devices",
            extra={"device_count": len(devices)}
        )
        
        return devices
    
    def transfer_playback(
        self,
        device_id: str,
        play: bool = True
    ) -> None:
        """
        Transfer playback to a different device.
        
        Args:
            device_id: Target device ID
            play: Start playback on new device
        """
        logger.info(
            "Transferring playback",
            extra={"device_id": device_id, "play": play}
        )
        
        body = {
            "device_ids": [device_id],
            "play": play
        }
        
        self._make_request(
            method="PUT",
            endpoint="/me/player",
            json_data=body,
            expected_status=204
        )
    
    # ==========================================================================
    # PLAYBACK STATE
    # ==========================================================================
    
    def get_playback_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current playback state.
        
        Returns:
            Playback state dictionary or None if no active playback
            
        Example:
            >>> state = client.get_playback_state()
            >>> if state:
            >>>     print(f"Playing: {state['is_playing']}")
            >>>     print(f"Track: {state['item']['name']}")
        """
        logger.debug("Getting playback state")
        
        try:
            response = self._make_request(
                method="GET",
                endpoint="/me/player",
                allow_204=True
            )
            
            if response is None:
                logger.debug("No active playback")
                return None
            
            logger.debug(
                "Playback state retrieved",
                extra={
                    "is_playing": response.get('is_playing'),
                    "device": response.get('device', {}).get('name')
                }
            )
            
            return response
            
        except SpotifyAPIError:
            return None
    
    def get_currently_playing(self) -> Optional[Dict[str, Any]]:
        """Get currently playing track (simplified version of get_playback_state)."""
        logger.debug("Getting currently playing track")
        
        try:
            response = self._make_request(
                method="GET",
                endpoint="/me/player/currently-playing",
                allow_204=True
            )
            
            return response
            
        except SpotifyAPIError:
            return None
    
    # ==========================================================================
    # HTTP REQUEST HANDLER
    # ==========================================================================
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        allow_204: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to Spotify API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/me/player/play")
            params: Query parameters
            json_data: JSON body data
            expected_status: Expected HTTP status code
            allow_204: Whether 204 No Content is acceptable
            
        Returns:
            Response JSON or None for 204 responses
            
        Raises:
            SpotifyAPIError: If request fails
            SpotifyRateLimitError: If rate limited
        """
        url = f"{SPOTIFY_API_BASE_URL}{endpoint}"
        headers = self._get_headers()
        
        last_exception = None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                start_time = time.time()
                
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=REQUEST_TIMEOUT
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log API call
                logger.debug(
                    f"Spotify API: {method} {endpoint}",
                    extra={
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2)
                    }
                )
                
                # Handle successful responses
                if response.status_code == expected_status:
                    if response.status_code == 204 or (allow_204 and response.status_code == 204):
                        return None
                    return response.json()
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', BASE_RETRY_DELAY))
                    
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            f"Rate limited, retrying after {retry_after}s",
                            extra={"attempt": attempt + 1, "retry_after": retry_after}
                        )
                        time.sleep(retry_after + RATE_LIMIT_MARGIN)
                        continue
                    else:
                        raise SpotifyRateLimitError(
                            message="Spotify API rate limit exceeded",
                            retry_after=retry_after,
                            status_code=429
                        )
                
                # Handle other errors
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                
                logger.error(
                    "Spotify API error",
                    extra={
                        "status_code": response.status_code,
                        "error_message": error_message,
                        "endpoint": endpoint
                    }
                )
                
                # Raise appropriate exception
                if response.status_code == 401:
                    raise SpotifyAuthenticationError(
                        message=error_message,
                        status_code=response.status_code,
                        response_body=response.text
                    )
                else:
                    raise SpotifyAPIError(
                        message=error_message,
                        status_code=response.status_code,
                        response_body=response.text
                    )
                    
            except requests.RequestException as e:
                last_exception = e
                
                if attempt < MAX_RETRIES:
                    delay = min(BASE_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    logger.warning(
                        f"Request failed, retrying in {delay}s",
                        extra={"attempt": attempt + 1, "error": str(e)}
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Request failed after retries",
                        extra={"attempts": MAX_RETRIES + 1, "error": str(e)},
                        exc_info=True
                    )
                    raise SpotifyAPIError(
                        message=f"Request failed: {str(e)}"
                    )
        
        # Should never reach here
        if last_exception:
            raise SpotifyAPIError(message=f"Request failed: {str(last_exception)}")
        raise SpotifyAPIError(message="Unknown error")

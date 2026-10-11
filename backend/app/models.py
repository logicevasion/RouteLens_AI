"""RouteLens-owned API models for selected geographic locations."""

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Location(BaseModel):
    """Canonical selected place shared by geocoding and journey inputs."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    latitude: float
    longitude: float
    address: str | None = Field(default=None, max_length=500)
    provider_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("name", "address", "provider_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("latitude", mode="before")
    @classmethod
    def valid_latitude(cls, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("latitude must be a finite number")
        if not -90 <= value <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return float(value)

    @field_validator("longitude", mode="before")
    @classmethod
    def valid_longitude(cls, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("longitude must be a finite number")
        if not -180 <= value <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return float(value)


class DestinationValidation(BaseModel):
    """Deterministic result for validating a selected destination."""

    valid: bool
    reason: str | None = None


class DrivingRouteRequest(BaseModel):
    """Canonical locations used to request approximate driving corridors."""

    model_config = ConfigDict(extra="forbid")

    origin: Location
    destination: Location


class RouteCandidate(BaseModel):
    """RouteLens-owned summary of one provider-generated route alternative."""

    model_config = ConfigDict(extra="forbid")

    id: str
    geometry: dict
    distance_meters: float
    duration_seconds: int
    label: str | None = None


class DrivingRoutesResponse(BaseModel):
    """Available driving candidates; an empty list means none were usable."""

    model_config = ConfigDict(extra="forbid")

    routes: list[RouteCandidate]

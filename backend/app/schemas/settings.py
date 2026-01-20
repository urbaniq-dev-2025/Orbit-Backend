"""
Schemas for Settings page APIs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# Password Change Schemas
class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., alias="newPassword", min_length=8)
    confirm_password: str = Field(..., alias="confirmPassword")

    class Config:
        allow_population_by_field_name = True


class PasswordChangeResponse(BaseModel):
    message: str
    last_password_change: datetime = Field(..., alias="lastPasswordChange")

    class Config:
        allow_population_by_field_name = True


# Avatar Upload Schemas
class AvatarUploadResponse(BaseModel):
    avatar_url: str = Field(..., alias="avatarUrl")
    message: str

    class Config:
        allow_population_by_field_name = True


# Security Status Schemas
class ActiveSession(BaseModel):
    id: uuid.UUID
    device: Optional[str] = None
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    location: Optional[str] = None
    last_active: datetime = Field(..., alias="lastActive")
    current: bool = False

    class Config:
        allow_population_by_field_name = True


class LoginActivityItem(BaseModel):
    timestamp: datetime
    ip_address: Optional[str] = Field(None, alias="ipAddress")
    device: Optional[str] = None
    location: Optional[str] = None
    success: bool
    failure_reason: Optional[str] = Field(None, alias="failureReason")

    class Config:
        allow_population_by_field_name = True


class SecurityStatusResponse(BaseModel):
    email_verified: bool = Field(..., alias="emailVerified")
    two_factor_enabled: bool = Field(..., alias="twoFactorEnabled")
    last_password_change: Optional[datetime] = Field(None, alias="lastPasswordChange")
    active_sessions: List[ActiveSession] = Field(default_factory=list, alias="activeSessions")
    recent_login_activity: List[LoginActivityItem] = Field(default_factory=list, alias="recentLoginActivity")

    class Config:
        allow_population_by_field_name = True


# Notification Preferences Schemas
class NotificationPreferenceItem(BaseModel):
    id: str  # preference_type
    label: str
    description: str
    enabled: bool
    channels: List[str]  # ['email', 'in-app', 'push']

    class Config:
        allow_population_by_field_name = True


class NotificationPreferencesResponse(BaseModel):
    preferences: List[NotificationPreferenceItem]

    class Config:
        allow_population_by_field_name = True


class NotificationPreferenceUpdate(BaseModel):
    id: str
    enabled: bool
    channels: List[str]


class NotificationPreferencesUpdateRequest(BaseModel):
    workspace_id: Optional[uuid.UUID] = Field(None, alias="workspaceId")
    preferences: List[NotificationPreferenceUpdate]

    class Config:
        allow_population_by_field_name = True


# Workspace Settings Schemas
class WorkspaceSettingsResponse(BaseModel):
    workspace_mode: str = Field(..., alias="workspaceMode")
    require_scope_approval: bool = Field(..., alias="requireScopeApproval")
    require_prd_approval: bool = Field(..., alias="requirePRDApproval")
    auto_create_project: bool = Field(..., alias="autoCreateProject")
    default_engagement_type: str = Field(..., alias="defaultEngagementType")
    ai_assist_enabled: bool = Field(..., alias="aiAssistEnabled")
    ai_model_preference: str = Field(..., alias="aiModelPreference")
    show_client_health: bool = Field(..., alias="showClientHealth")
    default_currency: str = Field(..., alias="defaultCurrency")
    timezone: str
    date_format: str = Field(..., alias="dateFormat")
    time_format: str = Field(..., alias="timeFormat")

    class Config:
        allow_population_by_field_name = True


class WorkspaceSettingsUpdate(BaseModel):
    workspace_mode: Optional[str] = Field(None, alias="workspaceMode")
    require_scope_approval: Optional[bool] = Field(None, alias="requireScopeApproval")
    require_prd_approval: Optional[bool] = Field(None, alias="requirePRDApproval")
    auto_create_project: Optional[bool] = Field(None, alias="autoCreateProject")
    default_engagement_type: Optional[str] = Field(None, alias="defaultEngagementType")
    ai_assist_enabled: Optional[bool] = Field(None, alias="aiAssistEnabled")
    ai_model_preference: Optional[str] = Field(None, alias="aiModelPreference")
    show_client_health: Optional[bool] = Field(None, alias="showClientHealth")
    default_currency: Optional[str] = Field(None, alias="defaultCurrency")
    timezone: Optional[str] = None
    date_format: Optional[str] = Field(None, alias="dateFormat")
    time_format: Optional[str] = Field(None, alias="timeFormat")

    class Config:
        allow_population_by_field_name = True


# Billing History Schemas
class PaymentMethod(BaseModel):
    type: str  # 'card', 'bank', etc.
    last4: Optional[str] = None
    brand: Optional[str] = None


class BillingHistoryItem(BaseModel):
    id: uuid.UUID
    description: str
    amount: float
    currency: str
    status: str  # 'paid', 'pending', 'failed', 'refunded'
    invoice_url: Optional[str] = Field(None, alias="invoiceUrl")
    billing_date: datetime = Field(..., alias="billingDate")
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    paid_at: Optional[datetime] = Field(None, alias="paidAt")
    payment_method: Optional[PaymentMethod] = Field(None, alias="paymentMethod")

    class Config:
        allow_population_by_field_name = True


class BillingHistoryResponse(BaseModel):
    history: List[BillingHistoryItem]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


# Teams Schemas
class TeamMemberItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID = Field(..., alias="userId")
    email: str
    full_name: str = Field(..., alias="fullName")
    role: str
    joined_at: datetime = Field(..., alias="joinedAt")

    class Config:
        allow_population_by_field_name = True


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    member_count: int = Field(..., alias="memberCount")
    role: Optional[str] = None  # Current user's role in this team
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        allow_population_by_field_name = True


class TeamListResponse(BaseModel):
    teams: List[TeamResponse]

    class Config:
        allow_population_by_field_name = True


class TeamCreate(BaseModel):
    workspace_id: uuid.UUID = Field(..., alias="workspaceId")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


class TeamMembersResponse(BaseModel):
    members: List[TeamMemberItem]

    class Config:
        allow_population_by_field_name = True


class TeamMemberAdd(BaseModel):
    user_id: uuid.UUID = Field(..., alias="userId")
    role: str = "member"

    class Config:
        allow_population_by_field_name = True


class TeamMemberUpdate(BaseModel):
    role: str

    class Config:
        allow_population_by_field_name = True


# 2FA Schemas
class TwoFactorEnableRequest(BaseModel):
    method: Literal["totp", "sms"] = "totp"
    phone_number: Optional[str] = Field(None, alias="phoneNumber")

    class Config:
        allow_population_by_field_name = True


class TwoFactorEnableResponse(BaseModel):
    qr_code: Optional[str] = Field(None, alias="qrCode")
    secret: Optional[str] = None
    backup_codes: List[str] = Field(default_factory=list, alias="backupCodes")
    message: str

    class Config:
        allow_population_by_field_name = True


class TwoFactorDisableRequest(BaseModel):
    password: str
    verification_code: str = Field(..., alias="verificationCode")

    class Config:
        allow_population_by_field_name = True


# Email Verification Schemas
class EmailVerificationSendResponse(BaseModel):
    message: str


class EmailVerificationRequest(BaseModel):
    token: str


class EmailVerificationResponse(BaseModel):
    message: str
    email_verified: bool = Field(..., alias="emailVerified")

    class Config:
        allow_population_by_field_name = True


# Data Export Schemas
class DataExportInclude(BaseModel):
    scopes: bool = True
    projects: bool = True
    clients: bool = True
    tasks: bool = True
    quotations: bool = True
    proposals: bool = True
    activity: bool = True


class DataExportRequest(BaseModel):
    workspace_id: Optional[uuid.UUID] = Field(None, alias="workspaceId")
    format: Literal["json", "csv", "xlsx"] = "json"
    include: DataExportInclude

    class Config:
        allow_population_by_field_name = True


class DataExportResponse(BaseModel):
    export_id: uuid.UUID = Field(..., alias="exportId")
    status: str  # 'processing', 'completed', 'failed'
    estimated_time: int = Field(..., alias="estimatedTime")
    message: str

    class Config:
        allow_population_by_field_name = True


class DataExportStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    format: str
    file_url: Optional[str] = Field(None, alias="fileUrl")
    file_size: Optional[int] = Field(None, alias="fileSize")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    created_at: datetime = Field(..., alias="createdAt")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")

    class Config:
        allow_population_by_field_name = True


class DataExportListResponse(BaseModel):
    exports: List[DataExportStatusResponse]
    total: int
    page: int
    page_size: int = Field(..., alias="pageSize")
    has_more: bool = Field(..., alias="hasMore")

    class Config:
        allow_population_by_field_name = True


# Account Deletion Schemas
class AccountDeletionRequest(BaseModel):
    password: str
    confirmation: str  # Must be "DELETE"


class AccountDeletionResponse(BaseModel):
    message: str

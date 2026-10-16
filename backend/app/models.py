"""API models (Pydantic). Persistence lives in db_models.py.

All analysis is produced by GPT Image 2 as images ("boards"). The user's age
is stored for the account only and is never sent to the image prompts.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

BoardKind = Literal["SEASON", "HAIR", "HAIR_COLOR", "OUTFIT", "ACCESSORIES"]
TryOnOp = Literal["HAIR", "HAIR_COLOR", "OUTFIT", "EYEWEAR"]
Operation = Literal["ORIGINAL", "BOARD", "HAIR", "HAIR_COLOR", "OUTFIT", "EYEWEAR"]
Option = Literal[1, 2, 3]
# Location for full-body outfit try-ons ("auto" = same as the board panel)
Setting = Literal["auto", "restaurant", "office", "garden", "city_street", "evening_event", "cafe"]
FeedbackType = Literal["LIKE", "DISLIKE", "SAVE", "TRY", "REGENERATE", "UNDO"]


# ---------------------------------------------------------------- users
class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    age: Optional[int]
    profile_complete: bool


class UserUpdate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=14, le=120)


# ---------------------------------------------------------------- profiles
class ImageNode(BaseModel):
    """Section 20 — every image is a node: try-ons form a tree from the original."""
    image_id: str
    parent_image_id: Optional[str] = None
    operation: Operation
    board_kind: Optional[BoardKind] = None
    reference_board_id: Optional[str] = None
    option: Optional[int] = None
    setting: Optional[str] = None
    prompt_version: Optional[str] = None
    quality: Optional[str] = None
    size: Optional[str] = None
    created_at: datetime


class FeedbackEntry(BaseModel):
    type: FeedbackType
    # Board options are addressed as "<board_image_id>:<option>", images by image_id.
    entity_type: Literal["board_option", "image"]
    entity_id: str = Field(max_length=64)


class UserFeedback(BaseModel):
    liked: list[str] = []
    disliked: list[str] = []
    saved: list[str] = []


class StyleRequest(BaseModel):
    selected_styles: list[str] = Field(min_length=1, max_length=2)
    trend_preference: Literal["low", "moderate", "high"] = "moderate"
    free_text_style_request: str = Field("", max_length=500)
    occasion: str = Field("", max_length=200)
    comfort_preferences: str = Field("", max_length=300)


class LumeraProfile(BaseModel):
    profile_version: str = "3.0"
    id: str
    status: Literal["created", "analyzed", "styled"]
    created_at: datetime
    updated_at: datetime
    original_image_id: Optional[str]
    # Current board per kind (older versions stay in `images`).
    boards: dict[str, str]
    style_request: Optional[StyleRequest]
    user_feedback: UserFeedback
    images: list[ImageNode]


class ProfileSummary(BaseModel):
    id: str
    status: str
    original_image_id: Optional[str]
    created_at: datetime


class TryOnRequest(BaseModel):
    operation: TryOnOp
    option: Option
    parent_image_id: Optional[str] = None
    mode: Literal["preview", "final"] = "preview"
    setting: Setting = "auto"  # used only by OUTFIT


class LookVisualizeRequest(BaseModel):
    parent_image_id: Optional[str] = None
    mode: Literal["preview", "final"] = "preview"
    include_eyewear: bool = True
    setting: Setting = "auto"

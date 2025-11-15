"""
Database Schemas for Snap Learn

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class Item(BaseModel):
    """
    Learning content items
    Collection: "item"
    """
    category: Literal[
        "alphabets","numbers","colors","shapes","animals","fruits","vegetables",
        "birds","days","months","family","body","seasons","weather","habits","opposites"
    ] = Field(..., description="Content category")
    key: str = Field(..., description="Unique key for the item within the category, e.g., 'A', '1', 'red'")
    label: str = Field(..., description="Human-friendly label, e.g., 'Apple', 'Red'")
    phonics: Optional[str] = Field(None, description="Phonics hint, e.g., 'A says ah' or IPA like /æ/")
    display: Optional[str] = Field(None, description="Optional display text or emoji for quick visuals")

class Progress(BaseModel):
    """
    User progress per device and category
    Collection: "progress"
    """
    device_id: str = Field(..., description="Client-generated device/session id")
    category: str = Field(..., description="Category name")
    points: int = Field(0, ge=0, description="Total points earned")
    correct: int = Field(0, ge=0, description="Total correct answers")
    attempts: int = Field(0, ge=0, description="Total attempts")
    badges: List[str] = Field(default_factory=list, description="Unlocked badges")

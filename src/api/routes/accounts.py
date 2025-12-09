"""
SIP Account Management Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from ...database.database import get_db
from ...database.models import User, SIPAccount
from .auth import get_current_user

router = APIRouter()


class SIPAccountCreate(BaseModel):
    account_name: str
    username: str
    password: str
    server_host: str
    server_port: int = 5060
    domain: str


class SIPAccountUpdate(BaseModel):
    account_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    server_host: Optional[str] = None
    server_port: Optional[int] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None


class SIPAccountResponse(BaseModel):
    id: int
    account_name: str
    username: str
    server_host: str
    server_port: int
    domain: str
    is_active: bool
    
    class Config:
        from_attributes = True


@router.post("", response_model=SIPAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_sip_account(
    account_data: SIPAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new SIP account."""
    account = SIPAccount(
        user_id=current_user.id,
        **account_data.dict()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=List[SIPAccountResponse])
async def list_sip_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all SIP accounts for current user."""
    accounts = db.query(SIPAccount).filter(
        SIPAccount.user_id == current_user.id
    ).all()
    return accounts


@router.get("/{account_id}", response_model=SIPAccountResponse)
async def get_sip_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific SIP account."""
    account = db.query(SIPAccount).filter(
        SIPAccount.id == account_id,
        SIPAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP account not found"
        )
    return account


@router.put("/{account_id}", response_model=SIPAccountResponse)
async def update_sip_account(
    account_id: int,
    account_data: SIPAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a SIP account."""
    account = db.query(SIPAccount).filter(
        SIPAccount.id == account_id,
        SIPAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP account not found"
        )
    
    update_data = account_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sip_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a SIP account."""
    account = db.query(SIPAccount).filter(
        SIPAccount.id == account_id,
        SIPAccount.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP account not found"
        )
    
    db.delete(account)
    db.commit()
    return None


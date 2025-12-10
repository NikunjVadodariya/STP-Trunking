"""
Call Management Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ...database.database import get_db
from ...database.models import User, SIPAccount, Call, CallRecord
from ...services.call_service import CallService
from .auth import get_current_user

router = APIRouter()


class CallCreate(BaseModel):
    sip_account_id: int
    to_uri: str


class CallResponse(BaseModel):
    id: int
    call_id: str
    from_uri: str
    to_uri: str
    direction: str
    state: str
    started_at: datetime
    connected_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[float] = None
    
    class Config:
        from_attributes = True


class CallStatusResponse(BaseModel):
    call_id: str
    state: str
    duration: Optional[float] = None


@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(
    call_data: CallCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Initiate a new call."""
    # Verify SIP account belongs to user
    sip_account = db.query(SIPAccount).filter(
        SIPAccount.id == call_data.sip_account_id,
        SIPAccount.user_id == current_user.id,
        SIPAccount.is_active == True
    ).first()
    if not sip_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SIP account not found or inactive"
        )
    
    # Use call service to initiate call
    call_service = CallService(db)
    call = await call_service.initiate_call(
        user_id=current_user.id,
        sip_account_id=sip_account.id,
        to_uri=call_data.to_uri
    )
    
    # Refresh to get latest state
    db.refresh(call)
    
    return call


@router.get("", response_model=List[CallResponse])
async def list_calls(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all calls for current user."""
    calls = db.query(Call).filter(
        Call.user_id == current_user.id
    ).order_by(Call.started_at.desc()).offset(skip).limit(limit).all()
    return calls


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific call."""
    call = db.query(Call).filter(
        Call.call_id == call_id,
        Call.user_id == current_user.id
    ).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    return call


@router.get("/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get call status."""
    call = db.query(Call).filter(
        Call.call_id == call_id,
        Call.user_id == current_user.id
    ).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    duration = None
    if call.connected_at:
        if call.ended_at:
            duration = (call.ended_at - call.connected_at).total_seconds()
        else:
            duration = (datetime.utcnow() - call.connected_at).total_seconds()
    
    return CallStatusResponse(
        call_id=call.call_id,
        state=call.state,
        duration=duration
    )


@router.post("/{call_id}/hangup", status_code=status.HTTP_200_OK)
async def hangup_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hang up a call."""
    call = db.query(Call).filter(
        Call.call_id == call_id,
        Call.user_id == current_user.id
    ).first()
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    # Use call service to hangup
    call_service = CallService(db)
    await call_service.hangup_call(call_id)
    
    return {"message": "Call terminated"}


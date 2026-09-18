"""
Consultation routes — the bridge API the frontend will call.

POST /consultations          -> save input, run the 4-agent CrewAI pipeline,
                                save every agent output, mark completed.
GET  /consultations          -> chat history for the logged-in user.
GET  /consultations/{id}     -> one consultation with all stored outputs.

Auth: every request needs  Authorization: Bearer <token>  from /auth/login.
"""

from fastapi import APIRouter, Depends, Header, HTTPException

from ..core.security import decode_access_token
from ..db.database import (
    create_consultation,
    get_consultations_for_user,
    get_consultation_by_id,
    complete_consultation,
)
from ..models.user_input import UserInput
from ..services.crew_service import run_consultation

router = APIRouter(prefix="/consultations", tags=["consultations"])


def get_current_user_id(authorization: str = Header(default="")) -> str:
    """Extract the logged-in user id from the JWT bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")

    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return payload["sub"]


@router.post("", status_code=201)
def start_consultation(
    payload: UserInput,
    user_id: str = Depends(get_current_user_id),
):
    """Save the user input, run the whole agent pipeline, store every output."""
    # 1) Save the consultation as in_progress (empty agent outputs).
    consultation = create_consultation(user_id, payload.model_dump(mode="json"))

    # 2) Run the CrewAI pipeline; each agent output is saved to MongoDB.
    def on_agent_done(agent_key: str, output: dict):
        print(f"  [progress] {agent_key} -> saved ({len(str(output))} chars)")

    run_consultation(consultation.id, payload.model_dump(mode="json"), progress=on_agent_done)

    # 3) Mark completed. (judge + blueprint_html filled in a later phase)
    complete_consultation(consultation.id, None, None)

    from ..models.consultation import Consultation
    doc = get_consultation_by_id(consultation.id)
    return Consultation.from_doc(doc).model_dump(mode="json")


@router.get("")
def chat_history(user_id: str = Depends(get_current_user_id)):
    """Return the logged-in user's past consultations (newest first)."""
    return get_consultations_for_user(user_id)


@router.get("/{consultation_id}")
def get_consultation(
    consultation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Return one consultation with all stored agent outputs."""
    doc = get_consultation_by_id(consultation_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Consultation not found.")

    if str(doc.get("user_id")) != user_id:
        raise HTTPException(status_code=403, detail="Not your consultation.")

    from ..models.consultation import Consultation
    return Consultation.from_doc(doc).model_dump(mode="json")
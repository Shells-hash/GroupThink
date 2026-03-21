from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.dependencies import get_db, get_current_user
from backend.models.user import User
from backend.models.thread import Thread
from backend.models.membership import GroupMembership
from backend.models.document import ThreadDocument
from backend.services.ai_service import draft_document
from backend.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter(tags=["documents"])


class DocCreate(BaseModel):
    title: str
    content: str = ""


class DocGenerateRequest(BaseModel):
    title: str
    instructions: str = ""


class DocUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class DocOut(BaseModel):
    id: int
    thread_id: int
    title: str
    content: str
    author_username: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _assert_thread_access(db: Session, thread_id: int, user_id: int) -> Thread:
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise NotFoundError("Thread not found")
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == thread.group_id,
        GroupMembership.user_id == user_id,
    ).first()
    if not membership:
        raise ForbiddenError("Not a member of this group")
    return thread


def _doc_out(doc: ThreadDocument) -> DocOut:
    return DocOut(
        id=doc.id,
        thread_id=doc.thread_id,
        title=doc.title,
        content=doc.content,
        author_username=doc.author.username if doc.author else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/threads/{thread_id}/docs", response_model=list[DocOut])
def list_docs(thread_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_thread_access(db, thread_id, current_user.id)
    docs = (
        db.query(ThreadDocument)
        .filter(ThreadDocument.thread_id == thread_id)
        .order_by(ThreadDocument.updated_at.desc())
        .all()
    )
    return [_doc_out(d) for d in docs]


@router.post("/threads/{thread_id}/docs", response_model=DocOut, status_code=status.HTTP_201_CREATED)
def create_doc(thread_id: int, body: DocCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_thread_access(db, thread_id, current_user.id)
    doc = ThreadDocument(thread_id=thread_id, title=body.title, content=body.content, author_id=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.post("/threads/{thread_id}/docs/generate", response_model=DocOut, status_code=status.HTTP_201_CREATED)
def generate_doc(thread_id: int, body: DocGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_thread_access(db, thread_id, current_user.id)
    content = draft_document(db, thread_id, body.title, "", body.instructions)
    doc = ThreadDocument(thread_id=thread_id, title=body.title, content=content, author_id=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.get("/docs/{doc_id}", response_model=DocOut)
def get_doc(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(ThreadDocument).filter(ThreadDocument.id == doc_id).first()
    if not doc:
        raise NotFoundError("Document not found")
    _assert_thread_access(db, doc.thread_id, current_user.id)
    return _doc_out(doc)


@router.put("/docs/{doc_id}", response_model=DocOut)
def update_doc(doc_id: int, body: DocUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(ThreadDocument).filter(ThreadDocument.id == doc_id).first()
    if not doc:
        raise NotFoundError("Document not found")
    _assert_thread_access(db, doc.thread_id, current_user.id)
    if body.title is not None:
        doc.title = body.title
    if body.content is not None:
        doc.content = body.content
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.delete("/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(ThreadDocument).filter(ThreadDocument.id == doc_id).first()
    if not doc:
        raise NotFoundError("Document not found")
    _assert_thread_access(db, doc.thread_id, current_user.id)
    db.delete(doc)
    db.commit()


@router.post("/docs/{doc_id}/ai-draft", response_model=DocOut)
def ai_draft_doc(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(ThreadDocument).filter(ThreadDocument.id == doc_id).first()
    if not doc:
        raise NotFoundError("Document not found")
    _assert_thread_access(db, doc.thread_id, current_user.id)
    new_content = draft_document(db, doc.thread_id, doc.title, doc.content)
    doc.content = new_content
    doc.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)

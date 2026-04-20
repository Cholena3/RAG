import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentListResponse, IngestionStatus
from app.middleware.auth import get_current_user
from app.services.embedding_service import EmbeddingService
from app.tasks.ingestion import ingest_document
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md", "csv"}


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    folder: str | None = Query(None),
    tags: str | None = Query(None),  # comma-separated
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    # Save file
    doc_id = uuid.uuid4()
    user_dir = os.path.join(settings.upload_dir, str(user.id))
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, f"{doc_id}.{ext}")
    with open(file_path, "wb") as f:
        f.write(content)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    doc = Document(
        id=doc_id,
        owner_id=user.id,
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        tags=tag_list,
        folder=folder,
        storage_path=file_path,
        status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Dispatch async ingestion
    ingest_document.delay(str(doc_id), file_path, ext)

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    folder: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(Document.owner_id == user.id)
    count_stmt = select(func.count(Document.id)).where(Document.owner_id == user.id)
    if folder:
        stmt = stmt.where(Document.folder == folder)
        count_stmt = count_stmt.where(Document.folder == folder)
    if status:
        stmt = stmt.where(Document.status == status)
        count_stmt = count_stmt.where(Document.status == status)
    stmt = stmt.order_by(Document.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    total = (await db.execute(count_stmt)).scalar()
    return DocumentListResponse(documents=result.scalars().all(), total=total)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: uuid.UUID, data: DocumentUpdate,
                          user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if data.tags is not None:
        doc.tags = data.tags
    if data.folder is not None:
        doc.folder = data.folder
    await db.flush()
    await db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Clean up vector store
    if doc.collection_id:
        EmbeddingService().delete_collection(doc.collection_id)
    # Clean up file
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)
    await db.delete(doc)


@router.get("/{document_id}/status", response_model=IngestionStatus)
async def get_ingestion_status(document_id: uuid.UUID, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return IngestionStatus(
        document_id=doc.id, status=doc.status,
        chunk_count=doc.chunk_count, error_message=doc.error_message,
    )


@router.get("/{document_id}/preview")
async def preview_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return document content for preview. PDFs return raw file, text types return extracted text."""
    from fastapi.responses import FileResponse, JSONResponse
    from app.services.document_processor import DocumentProcessor

    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not os.path.exists(doc.storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # For PDFs, serve the raw file so the frontend can render it
    if doc.file_type == "pdf":
        return FileResponse(
            doc.storage_path,
            media_type="application/pdf",
            filename=doc.filename,
        )

    # For text-based formats, extract and return text
    processor = DocumentProcessor()
    try:
        text, _ = processor.extract_text(doc.storage_path, doc.file_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {e}")

    return JSONResponse(content={
        "document_id": str(doc.id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "content": text[:50000],  # cap preview at 50k chars
    })


@router.post("/bulk-upload", response_model=list[DocumentResponse], status_code=201)
async def bulk_upload_documents(
    files: list[UploadFile] = File(...),
    folder: str | None = Query(None),
    tags: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple documents at once."""
    results = []
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            continue  # skip unsupported, don't fail the whole batch

        content = await file.read()
        if len(content) > settings.max_file_size_mb * 1024 * 1024:
            continue

        doc_id = uuid.uuid4()
        user_dir = os.path.join(settings.upload_dir, str(user.id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{doc_id}.{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        doc = Document(
            id=doc_id,
            owner_id=user.id,
            filename=file.filename,
            file_type=ext,
            file_size=len(content),
            tags=tag_list,
            folder=folder,
            storage_path=file_path,
            status="pending",
        )
        db.add(doc)
        await db.flush()
        await db.refresh(doc)

        ingest_document.delay(str(doc_id), file_path, ext)
        results.append(doc)

    return results

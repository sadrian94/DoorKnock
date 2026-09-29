from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
from ..documents import get_job_documents_info, resolve_document_file_path, generate_download_filename
from .. import crud
from ..tailor.engine import tailor_application_documents
import logging

logger = logging.getLogger("doorknock.api.documents")

router = APIRouter(prefix="/api/jobs", tags=["documents"])

@router.get("/{job_id}/documents")
def get_documents_status(job_id: str):
    """Retrieve metadata about available generated documents (Resume & Cover Letter) for a job."""
    return get_job_documents_info(job_id)

@router.get("/{job_id}/documents/{doc_type}")
def get_document_pdf(
    job_id: str,
    doc_type: str,
    version: Optional[str] = Query(None, description="Specific version, e.g., 'v001' or 'v002'"),
    download: bool = Query(False, description="Whether to trigger download or inline preview")
):
    """Serve the requested document (Resume or Cover Letter) PDF inline or as attachment."""
    normalized_type = doc_type.replace("-", "_")
    if normalized_type not in ["resume", "cover_letter"]:
        raise HTTPException(status_code=400, detail="Invalid doc_type. Must be 'resume' or 'cover_letter'")

    file_path = resolve_document_file_path(job_id, normalized_type, version=version)
    if not file_path or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"No {normalized_type} PDF found for this job")

    custom_filename = generate_download_filename(job_id, normalized_type, version=version)
    disposition = "attachment" if download else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{custom_filename}"'
    }
    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        headers=headers
    )

@router.post("/{job_id}/tailor/{doc_type}")
async def trigger_document_tailoring(job_id: str, doc_type: str):
    """Generate one independently versioned resume or cover letter."""
    normalized_type = doc_type.replace("-", "_")
    if normalized_type not in ("resume", "cover_letter"):
        raise HTTPException(status_code=400, detail="Invalid doc_type. Must be 'resume' or 'cover-letter'")
    job = crud.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        result = await tailor_application_documents(job, document_type=normalized_type)
        if not result.get("success"):
            compilation = result.get("compilation") or {}
            if compilation.get("error"):
                reason = f"Typst compilation failed: {compilation['error']}"
            elif compilation.get("page_limit_required") and compilation.get("page_count", 0) > 1:
                reason = f"Document exceeds one page ({compilation['page_count']} pages)"
            elif not compilation.get("text_complete", False):
                reason = "PDF text or required sections failed validation"
            else:
                reason = "Document tailoring or Typst compilation failed"
            raise HTTPException(status_code=500, detail=reason)

        return {
            "status": "success",
            "message": f"{doc_type} tailored and compiled with Typst successfully",
            "document_type": normalized_type,
            "documents_info": get_job_documents_info(job_id),
            "manifest": result.get("manifest"),
        }
    except ValueError as e:
        logger.warning("Document generation needs updated job analysis for %s: %s", job_id, e)
        raise HTTPException(status_code=409, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to tailor documents for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import APIRouter, Depends, HTTPException

from toolatlas_mcp.api.schemas import (
    DomainCreate,
    DomainResponse,
    GlossaryTermCreate,
    GlossaryTermResponse,
    GlossaryTermUpdate,
)
from toolatlas_mcp.db import get_storage
from toolatlas_mcp.registry.storage import StorageBackend

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


@router.get("/terms")
async def list_terms(storage: StorageBackend = Depends(get_storage)):
    terms = await storage.list_glossary_terms()
    return [GlossaryTermResponse(**t) for t in terms]


@router.post("/terms", status_code=201)
async def create_term(body: GlossaryTermCreate, storage: StorageBackend = Depends(get_storage)):
    term = await storage.create_glossary_term(
        term=body.term,
        definition=body.definition,
    )
    return GlossaryTermResponse(**term)


@router.get("/terms/{term_id}")
async def get_term(term_id: str, storage: StorageBackend = Depends(get_storage)):
    term = await storage.get_glossary_term(term_id)
    if not term:
        raise HTTPException(404, "Glossary term not found")
    return GlossaryTermResponse(**term)


@router.patch("/terms/{term_id}")
async def update_term(term_id: str, body: GlossaryTermUpdate, storage: StorageBackend = Depends(get_storage)):
    kwargs = body.model_dump(exclude_unset=True)
    term = await storage.update_glossary_term(term_id, **kwargs)
    if not term:
        raise HTTPException(404, "Glossary term not found")
    return GlossaryTermResponse(**term)


@router.delete("/terms/{term_id}")
async def delete_term(term_id: str, storage: StorageBackend = Depends(get_storage)):
    deleted = await storage.delete_glossary_term(term_id)
    if not deleted:
        raise HTTPException(404, "Glossary term not found")
    return {"ok": True}


@router.get("/domains")
async def list_domains(storage: StorageBackend = Depends(get_storage)):
    domains = await storage.list_domains()
    return [DomainResponse(**d) for d in domains]


@router.post("/domains", status_code=201)
async def create_domain(body: DomainCreate, storage: StorageBackend = Depends(get_storage)):
    domain = await storage.create_domain(
        name=body.name,
        description=body.description,
    )
    return DomainResponse(**domain)

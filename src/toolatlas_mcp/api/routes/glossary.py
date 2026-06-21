from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from toolatlas_mcp.api.schemas import (
    DomainCreate,
    DomainResponse,
    GlossaryTermCreate,
    GlossaryTermResponse,
    GlossaryTermUpdate,
)
from toolatlas_mcp.db import get_db
from toolatlas_mcp.registry.repository import RegistryRepository

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


@router.get("/terms")
async def list_terms(db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    terms = await repo.list_glossary_terms()
    return [GlossaryTermResponse.model_validate(t) for t in terms]


@router.post("/terms", status_code=201)
async def create_term(body: GlossaryTermCreate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    term = await repo.create_glossary_term(
        term=body.term,
        definition=body.definition,
    )
    return GlossaryTermResponse.model_validate(term)


@router.get("/terms/{term_id}")
async def get_term(term_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    term = await repo.get_glossary_term(term_id)
    if not term:
        raise HTTPException(404, "Glossary term not found")
    return GlossaryTermResponse.model_validate(term)


@router.patch("/terms/{term_id}")
async def update_term(term_id: str, body: GlossaryTermUpdate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    kwargs = body.model_dump(exclude_unset=True)
    term = await repo.update_glossary_term(term_id, **kwargs)
    if not term:
        raise HTTPException(404, "Glossary term not found")
    return GlossaryTermResponse.model_validate(term)


@router.delete("/terms/{term_id}")
async def delete_term(term_id: str, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    deleted = await repo.delete_glossary_term(term_id)
    if not deleted:
        raise HTTPException(404, "Glossary term not found")
    return {"ok": True}


@router.get("/domains")
async def list_domains(db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    domains = await repo.list_domains()
    return [DomainResponse.model_validate(d) for d in domains]


@router.post("/domains", status_code=201)
async def create_domain(body: DomainCreate, db: AsyncSession = Depends(get_db)):
    repo = RegistryRepository(db)
    domain = await repo.create_domain(
        name=body.name,
        description=body.description,
    )
    return DomainResponse.model_validate(domain)

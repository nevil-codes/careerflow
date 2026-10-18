from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.deps import SessionDep, get_or_404
from app.llm.base import ProviderError, ProviderUnavailable
from app.llm.probe import ProviderTestResult, run_probe
from app.llm.registry import DEFAULT_BASE_URLS, build_provider
from app.models import ProviderConfig, ProviderConfigCreate, ProviderConfigRead, ProviderConfigUpdate

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=list[ProviderConfigRead])
def list_providers(session: SessionDep) -> list[ProviderConfig]:
    return list(session.exec(select(ProviderConfig).order_by(ProviderConfig.id)))


@router.get("/defaults")
def provider_defaults() -> dict[str, dict[str, str]]:
    """Default base URL per provider kind, for pre-filling forms."""
    return {"base_urls": DEFAULT_BASE_URLS}


@router.post("", response_model=ProviderConfigRead, status_code=201)
def create_provider(data: ProviderConfigCreate, session: SessionDep) -> ProviderConfig:
    config = ProviderConfig.model_validate(
        data, update={"base_url": data.base_url or DEFAULT_BASE_URLS[data.provider]}
    )
    if config.enabled:
        _disable_others(session, None)
    session.add(config)
    _commit(session)
    session.refresh(config)
    return config


@router.patch("/{provider_id}", response_model=ProviderConfigRead)
def update_provider(provider_id: int, data: ProviderConfigUpdate, session: SessionDep) -> ProviderConfig:
    config = get_or_404(session, ProviderConfig, provider_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("enabled"):
        _disable_others(session, config.id)
    config.sqlmodel_update(changes)
    _commit(session)
    session.refresh(config)
    return config


@router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: int, session: SessionDep) -> None:
    session.delete(get_or_404(session, ProviderConfig, provider_id))
    session.commit()


@router.get("/{provider_id}/models", response_model=list[str])
def list_models(provider_id: int, session: SessionDep) -> list[str]:
    provider = build_provider(get_or_404(session, ProviderConfig, provider_id))
    try:
        return provider.list_models()
    except ProviderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
def test_provider(provider_id: int, session: SessionDep) -> ProviderTestResult:
    """Runs a small structured request. Always 200; check ``ok`` and ``error``."""
    return run_probe(build_provider(get_or_404(session, ProviderConfig, provider_id)))


def _disable_others(session: Session, keep_id: int | None) -> None:
    """Only one provider is enabled at a time."""
    for other in session.exec(select(ProviderConfig).where(ProviderConfig.enabled)):
        if other.id != keep_id:
            other.enabled = False


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "A provider with that name already exists.") from exc

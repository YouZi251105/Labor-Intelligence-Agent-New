from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.routes import (
    admin,
    admin_dictionary,
    admin_rule_packages,
    analytics,
    auth,
    cases,
    collaboration,
    documents,
    evidence,
    evidence_rules,
    help,
    lawyer,
    lawyer_service,
    meta,
    profile,
    simulations,
    workflow,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(help.router)
api_router.include_router(analytics.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
api_router.include_router(evidence_rules.router)
api_router.include_router(simulations.router)
api_router.include_router(documents.router)
api_router.include_router(workflow.router)
api_router.include_router(lawyer.router)
api_router.include_router(lawyer_service.router)
api_router.include_router(collaboration.router)
api_router.include_router(collaboration.admin_router)
api_router.include_router(admin_rule_packages.router)
api_router.include_router(admin_dictionary.router)
api_router.include_router(admin.router)

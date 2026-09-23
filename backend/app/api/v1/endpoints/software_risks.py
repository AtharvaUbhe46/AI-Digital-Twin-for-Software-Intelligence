import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.project import Project
from app.models.risk import SoftwareRisk
from app.schemas.software_risk import (
    SoftwareRiskResponse,
    RiskSummaryResponse,
)
from app.services.risk.risk_service import risk_service

logger = logging.getLogger("digital_twin.api.risks")
router = APIRouter()


@router.get(
    "/projects/{project_id}/risks",
    response_model=List[SoftwareRiskResponse],
    summary="Get Detected Software Risks",
    description="Returns detected risks with filters for severity, status, and risk_type. Evaluates rules on-demand if not yet run.",
)
async def get_software_risks(
    project_id: int,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: OPEN, ACKNOWLEDGED, RESOLVED"),
    severity_filter: Optional[str] = Query(None, alias="severity", description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    risk_type: Optional[str] = Query(None, description="Filter by specific risk type"),
    db: Session = Depends(get_db),
):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    # If project has 0 risk records total, trigger an initial evaluation
    existing_count = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == project_id).count()
    if existing_count == 0:
        try:
            risk_service.evaluate_and_persist_risks(project_id, db)
        except Exception as e:
            logger.error(f"Error evaluating initial risks for project {project_id}: {str(e)}", exc_info=True)

    risks = risk_service.get_risks(
        project_id=project_id,
        db=db,
        status=status_filter,
        severity=severity_filter,
        risk_type=risk_type,
    )

    return [
        SoftwareRiskResponse(
            id=r.id,
            project_id=r.project_id,
            risk_type=r.risk_type,
            title=r.title,
            description=r.description,
            severity=r.severity,
            status=r.status,
            fingerprint=r.fingerprint,
            detection_rule=r.detection_rule,
            metric_value=r.metric_value,
            threshold_value=r.threshold_value,
            evidence=r.evidence or {},
            affected_entities=r.affected_entities or [],
            detected_at=r.detected_at,
            acknowledged_at=r.acknowledged_at,
            resolved_at=r.resolved_at,
        )
        for r in risks
    ]


@router.get(
    "/projects/{project_id}/risks/summary",
    response_model=RiskSummaryResponse,
    summary="Get Risk Severity & Status Summary",
    description="Returns aggregate counts of detected risks grouped by severity and lifecycle status.",
)
async def get_risks_summary(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    risks = db.query(SoftwareRisk).filter(SoftwareRisk.project_id == project_id).all()

    # Active risks (OPEN or ACKNOWLEDGED) for severity counts
    active_risks = [r for r in risks if r.status != "RESOLVED"]

    return RiskSummaryResponse(
        total_risks=len(active_risks),
        critical_count=sum(1 for r in active_risks if r.severity == "CRITICAL"),
        high_count=sum(1 for r in active_risks if r.severity == "HIGH"),
        medium_count=sum(1 for r in active_risks if r.severity == "MEDIUM"),
        low_count=sum(1 for r in active_risks if r.severity == "LOW"),
        open_count=sum(1 for r in risks if r.status == "OPEN"),
        acknowledged_count=sum(1 for r in risks if r.status == "ACKNOWLEDGED"),
        resolved_count=sum(1 for r in risks if r.status == "RESOLVED"),
    )


@router.get(
    "/projects/{project_id}/risks/{risk_id}",
    response_model=SoftwareRiskResponse,
    summary="Get Specific Risk Detail",
    description="Returns complete details, configured threshold, and granular evidence for a specific detected risk.",
)
async def get_risk_detail(project_id: int, risk_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    risk = risk_service.get_risk_by_id(risk_id, project_id, db)
    if not risk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Risk {risk_id} not found for this project")

    return SoftwareRiskResponse(
        id=risk.id,
        project_id=risk.project_id,
        risk_type=risk.risk_type,
        title=risk.title,
        description=risk.description,
        severity=risk.severity,
        status=risk.status,
        fingerprint=risk.fingerprint,
        detection_rule=risk.detection_rule,
        metric_value=risk.metric_value,
        threshold_value=risk.threshold_value,
        evidence=risk.evidence or {},
        affected_entities=risk.affected_entities or [],
        detected_at=risk.detected_at,
        acknowledged_at=risk.acknowledged_at,
        resolved_at=risk.resolved_at,
    )


@router.post(
    "/projects/{project_id}/risks/{risk_id}/acknowledge",
    response_model=SoftwareRiskResponse,
    summary="Acknowledge a Detected Risk",
    description="Transitions an OPEN risk to ACKNOWLEDGED state.",
)
async def acknowledge_risk(project_id: int, risk_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    try:
        risk = risk_service.acknowledge_risk(risk_id, project_id, db)
        return SoftwareRiskResponse(
            id=risk.id,
            project_id=risk.project_id,
            risk_type=risk.risk_type,
            title=risk.title,
            description=risk.description,
            severity=risk.severity,
            status=risk.status,
            fingerprint=risk.fingerprint,
            detection_rule=risk.detection_rule,
            metric_value=risk.metric_value,
            threshold_value=risk.threshold_value,
            evidence=risk.evidence or {},
            affected_entities=risk.affected_entities or [],
            detected_at=risk.detected_at,
            acknowledged_at=risk.acknowledged_at,
            resolved_at=risk.resolved_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error acknowledging risk {risk_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/projects/{project_id}/risks/{risk_id}/resolve",
    response_model=SoftwareRiskResponse,
    summary="Resolve a Detected Risk",
    description="Transitions an OPEN or ACKNOWLEDGED risk to RESOLVED state.",
)
async def resolve_risk(project_id: int, risk_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    try:
        risk = risk_service.resolve_risk(risk_id, project_id, db)
        return SoftwareRiskResponse(
            id=risk.id,
            project_id=risk.project_id,
            risk_type=risk.risk_type,
            title=risk.title,
            description=risk.description,
            severity=risk.severity,
            status=risk.status,
            fingerprint=risk.fingerprint,
            detection_rule=risk.detection_rule,
            metric_value=risk.metric_value,
            threshold_value=risk.threshold_value,
            evidence=risk.evidence or {},
            affected_entities=risk.affected_entities or [],
            detected_at=risk.detected_at,
            acknowledged_at=risk.acknowledged_at,
            resolved_at=risk.resolved_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving risk {risk_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/projects/{project_id}/risks/recalculate",
    response_model=List[SoftwareRiskResponse],
    summary="Recalculate Risks",
    description="Forces re-evaluation of all risk rules against current project data.",
)
async def recalculate_risks(project_id: int, db: Session = Depends(get_db)):
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

    try:
        risks = risk_service.evaluate_and_persist_risks(project_id, db)
        return [
            SoftwareRiskResponse(
                id=r.id,
                project_id=r.project_id,
                risk_type=r.risk_type,
                title=r.title,
                description=r.description,
                severity=r.severity,
                status=r.status,
                fingerprint=r.fingerprint,
                detection_rule=r.detection_rule,
                metric_value=r.metric_value,
                threshold_value=r.threshold_value,
                evidence=r.evidence or {},
                affected_entities=r.affected_entities or [],
                detected_at=r.detected_at,
                acknowledged_at=r.acknowledged_at,
                resolved_at=r.resolved_at,
            )
            for r in risks
        ]
    except Exception as e:
        logger.error(f"Error recalculating risks for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Risk evaluation failed: {str(e)}")

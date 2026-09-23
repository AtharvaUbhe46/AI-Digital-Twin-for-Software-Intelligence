import logging
from typing import List
from sqlalchemy.orm import Session

from app.services.risk.risk_rules import ALL_RISK_RULES, BaseRiskRule, RiskDetectionResult

logger = logging.getLogger("digital_twin.risk_engine")


class RiskEngine:
    """
    Evaluates enabled risk rules against normalized repository telemetry.
    """

    def __init__(self, rules: List[BaseRiskRule] = None):
        self.rules = rules or ALL_RISK_RULES

    def evaluate_rules(self, project_id: int, db: Session) -> List[RiskDetectionResult]:
        logger.info(f"Evaluating {len(self.rules)} risk rules for project_id={project_id}")
        detected_risks: List[RiskDetectionResult] = []

        for rule in self.rules:
            try:
                result = rule.evaluate(project_id, db)
                if result:
                    detected_risks.append(result)
                    logger.info(f"Rule [{rule.rule_id}] triggered risk: {result.title} ({result.severity})")
            except Exception as e:
                logger.error(f"Error evaluating rule [{rule.rule_id}] for project {project_id}: {str(e)}", exc_info=True)

        return detected_risks


risk_engine = RiskEngine()

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from app.models.evolution import ChangeHotspot
from app.models.project import Project, Commit

logger = logging.getLogger("digital_twin.hotspot_service")


class HotspotAnalysisService:
    """
    Analyzes modules and files that experience frequent changes, additions, and deletions.
    Strictly classified as 'Change Hotspots' to indicate active maintenance focal points,
    NOT flawed code or problematic engineers.
    """

    @staticmethod
    def get_change_hotspots(
        project_id: int,
        db: Session,
        limit: int = 50,
        sort_by: str = "changes"
    ) -> Dict[str, Any]:
        """
        Retrieves change hotspots for a given project from PostgreSQL.
        Supported sort_by: "changes", "churn", "recent", "contributors".
        """
        query = db.query(ChangeHotspot).filter(ChangeHotspot.project_id == project_id)

        if sort_by == "churn":
            query = query.order_by(desc(ChangeHotspot.churn), desc(ChangeHotspot.change_count))
        elif sort_by == "recent":
            query = query.order_by(desc(ChangeHotspot.last_changed_at), desc(ChangeHotspot.change_count))
        elif sort_by == "contributors":
            query = query.order_by(desc(ChangeHotspot.contributor_count), desc(ChangeHotspot.change_count))
        else:  # default: "changes"
            query = query.order_by(desc(ChangeHotspot.change_count), desc(ChangeHotspot.churn))

        hotspots = query.limit(limit).all()

        results = []
        for h in hotspots:
            results.append({
                "id": h.id,
                "path": h.path,
                "change_count": h.change_count,
                "additions": h.additions,
                "deletions": h.deletions,
                "churn": h.churn if h.churn is not None else (h.additions + h.deletions),
                "contributor_count": h.contributor_count,
                "last_changed_at": h.last_changed_at.isoformat() if h.last_changed_at else None,
            })

        has_data = len(results) > 0

        return {
            "project_id": project_id,
            "has_sufficient_data": has_data,
            "hotspots": results,
            "total_analyzed_files": len(results),
            "definition": (
                "Change Hotspots identify files/modules with frequent commits and code churn. "
                "Highlights active development areas; does NOT denote defect density or bad code."
            )
        }

    @staticmethod
    def record_file_modifications(
        project_id: int,
        file_modifications: List[Dict[str, Any]],
        commit_date: Optional[datetime],
        author_login: Optional[str],
        db: Session
    ) -> None:
        """
        Records or updates file modification metrics in change_hotspots table.
        file_modifications: list of dicts with keys: 'filename', 'additions', 'deletions'
        """
        for mod in file_modifications:
            filepath = mod.get("filename")
            if not filepath:
                continue

            additions = int(mod.get("additions") or 0)
            deletions = int(mod.get("deletions") or 0)
            churn = additions + deletions

            hotspot = db.query(ChangeHotspot).filter(
                ChangeHotspot.project_id == project_id,
                ChangeHotspot.path == filepath
            ).first()

            if not hotspot:
                hotspot = ChangeHotspot(
                    project_id=project_id,
                    path=filepath,
                    change_count=1,
                    additions=additions,
                    deletions=deletions,
                    churn=churn,
                    contributor_count=1,
                    last_changed_at=commit_date or datetime.now(timezone.utc)
                )
                db.add(hotspot)
            else:
                hotspot.change_count += 1
                hotspot.additions += additions
                hotspot.deletions += deletions
                hotspot.churn += churn
                if commit_date and (hotspot.last_changed_at is None or commit_date > hotspot.last_changed_at):
                    hotspot.last_changed_at = commit_date

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not persist hotspot updates for project {project_id}: {e}")


hotspot_service = HotspotAnalysisService()

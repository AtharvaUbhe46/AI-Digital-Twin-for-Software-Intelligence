import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.simulation import (
    SimulationBaselineResponse,
    SimulationCreateRequest,
    SimulationResponse,
    SimulationSummaryResponse,
    SimulationCompareResponse,
)
from app.services.simulation_service import simulation_engine

logger = logging.getLogger("digital_twin.api.simulation")

router = APIRouter(prefix="/projects", tags=["What-If Simulation"])


@router.get(
    "/{project_id}/simulations/baseline",
    response_model=SimulationBaselineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Simulation Baseline & Parameters",
    description="Returns current project state from Digital Twin to act as baseline, along with supported simulation parameters.",
)
def get_simulation_baseline(
    project_id: int,
    db: Session = Depends(get_db),
):
    try:
        return simulation_engine.get_baseline(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching baseline for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch baseline: {str(e)}")


@router.get(
    "/{project_id}/simulations",
    response_model=List[SimulationSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Saved Simulations",
    description="Returns history of saved What-If simulations for a project.",
)
def list_simulations(
    project_id: int,
    db: Session = Depends(get_db),
):
    try:
        return simulation_engine.get_simulations(project_id, db)
    except Exception as e:
        logger.error(f"Error listing simulations for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list simulations: {str(e)}")


@router.post(
    "/{project_id}/simulations",
    response_model=SimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Run What-If Simulation",
    description="Evaluates a hypothetical change scenario against project Digital Twin baseline in an isolated in-memory calculation.",
)
def create_simulation(
    project_id: int,
    request: SimulationCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        return simulation_engine.simulate(project_id=project_id, request=request, db=db, persist=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing simulation for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to execute simulation: {str(e)}")


@router.get(
    "/{project_id}/simulations/{simulation_id}",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Simulation Details",
    description="Retrieves full inputs, simulated metrics, impact analysis, and health impact for a specific simulation.",
)
def get_simulation_detail(
    project_id: int,
    simulation_id: int,
    db: Session = Depends(get_db),
):
    try:
        return simulation_engine.get_simulation_detail(project_id, simulation_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving simulation {simulation_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get simulation: {str(e)}")


@router.delete(
    "/{project_id}/simulations/{simulation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Saved Simulation",
    description="Deletes a saved simulation. Never deletes baseline project snapshots or real repository records.",
)
def delete_simulation(
    project_id: int,
    simulation_id: int,
    db: Session = Depends(get_db),
):
    try:
        simulation_engine.delete_simulation(project_id, simulation_id, db)
        return {"deleted": True, "simulation_id": simulation_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting simulation {simulation_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete simulation: {str(e)}")


@router.get(
    "/{project_id}/simulations/compare/{sim_a_id}/{sim_b_id}",
    response_model=SimulationCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Two Simulations",
    description="Compares two saved simulations side-by-side, displaying parameter differences, metric comparisons, and risk trade-offs.",
)
def compare_simulations(
    project_id: int,
    sim_a_id: int,
    sim_b_id: int,
    db: Session = Depends(get_db),
):
    try:
        return simulation_engine.compare_simulations(project_id, sim_a_id, sim_b_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing simulations {sim_a_id} and {sim_b_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to compare simulations: {str(e)}")


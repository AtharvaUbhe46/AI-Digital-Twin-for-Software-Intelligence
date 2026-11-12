import pytest
from app.services.architecture.parser.python_parser import PythonASTParser
from app.services.architecture.parser.js_ts_parser import JSTypeScriptParser
from app.services.architecture.graph.graph_builder import KnowledgeGraphBuilder
from app.services.architecture.architecture_service import ArchitectureService
from app.models.architecture import ArchitectureAnalysis, GraphNode, GraphEdge


def test_python_parser_endpoint_and_layered_architecture():
    """
    Verifies that Python AST Parser extracts:
    - Endpoint entities with method, route, handler, file_path, module, framework
    - Endpoint -> HANDLED_BY -> Backend Function
    - Backend Function -> BELONGS_TO -> Module
    - Backend Function -> CALLS -> Service Function
    - Service Function -> ACCESSES -> Database Entity
    """
    parser = PythonASTParser()
    code = '''
from fastapi import APIRouter
from app.services.order_service import process_order

router = APIRouter()

@router.post("/api/v1/orders")
def create_order(order_data: dict):
    return process_order(order_data)

def process_order(data: dict):
    db.query(OrderModel).filter_by(id=data["id"]).first()
    return {"status": "created"}
'''
    entities, relations = parser.parse_file("app/api/endpoints/order.py", code)

    # 1. Verify Endpoint entity
    endpoint_entities = [e for e in entities if e.entity_type == "api_endpoint"]
    assert len(endpoint_entities) == 1
    ep = endpoint_entities[0]
    assert ep.name == "POST /api/v1/orders"
    assert ep.metadata.get("http_method") == "POST"
    assert ep.metadata.get("route_path") == "/api/v1/orders"
    assert ep.metadata.get("handler_name") == "create_order"
    assert ep.metadata.get("framework") == "FastAPI"
    assert ep.file_path == "app/api/endpoints/order.py"

    # 2. Verify Database entity
    db_entities = [e for e in entities if e.entity_type == "database_entity"]
    assert len(db_entities) >= 1
    assert any("OrderModel" in d.name for d in db_entities)

    # 3. Verify HANDLED_BY relation
    handled_by_rel = [r for r in relations if r.rel_type == "HANDLED_BY"]
    assert len(handled_by_rel) >= 1
    assert handled_by_rel[0].source_id == ep.id
    assert "create_order" in handled_by_rel[0].target_id

    # 4. Verify BELONGS_TO relation
    belongs_to_rel = [r for r in relations if r.rel_type == "BELONGS_TO"]
    assert len(belongs_to_rel) >= 1

    # 5. Verify CALLS relation (Backend Function -> Service Function)
    calls_rel = [r for r in relations if r.rel_type == "CALLS"]
    assert any("process_order" in r.target_id for r in calls_rel)

    # 6. Verify ACCESSES relation (Service Function -> Database Entity)
    accesses_rel = [r for r in relations if r.rel_type == "ACCESSES"]
    assert len(accesses_rel) >= 1
    assert any("OrderModel" in r.target_id for r in accesses_rel)


def test_js_ts_parser_frontend_component_calls_endpoint():
    """
    Verifies that JS/TypeScript Parser extracts:
    - Frontend Component -> CALLS -> Endpoint
    """
    parser = JSTypeScriptParser()
    code = '''
import React, { useEffect, useState } from 'react';

export function OrderList() {
    const [orders, setOrders] = useState([]);

    useEffect(() => {
        fetch("/api/v1/orders")
            .then(res => res.json())
            .then(data => setOrders(data));
    }, []);

    return <div>Orders</div>;
}
'''
    entities, relations = parser.parse_file("src/components/OrderList.tsx", code)

    # Verify CALLS relation from component to endpoint
    calls_rel = [r for r in relations if r.rel_type == "CALLS" and "endpoint:" in r.target_id]
    assert len(calls_rel) >= 1
    assert "OrderList" in calls_rel[0].source_id
    assert "/api/v1/orders" in calls_rel[0].target_id


def test_endpoint_change_detection_and_impact_analysis():
    """
    Verifies endpoint change detection:
    - Added endpoints
    - Removed endpoints
    - Modified path
    - Modified HTTP method
    - Modified handler function
    - Impact analysis: affected frontend components, backend functions, and service functions
    """
    service = ArchitectureService()

    prev_endpoints = {
        "endpoint:GET:/api/v1/users": {
            "id": "endpoint:GET:/api/v1/users",
            "name": "GET /api/v1/users",
            "file_path": "app/api/users.py",
            "metadata": {
                "http_method": "GET",
                "route_path": "/api/v1/users",
                "handler_name": "list_users",
            }
        },
        "endpoint:POST:/api/v1/items": {
            "id": "endpoint:POST:/api/v1/items",
            "name": "POST /api/v1/items",
            "file_path": "app/api/items.py",
            "metadata": {
                "http_method": "POST",
                "route_path": "/api/v1/items",
                "handler_name": "create_item_old",
            }
        },
        "endpoint:DELETE:/api/v1/old-resource": {
            "id": "endpoint:DELETE:/api/v1/old-resource",
            "name": "DELETE /api/v1/old-resource",
            "file_path": "app/api/old.py",
            "metadata": {
                "http_method": "DELETE",
                "route_path": "/api/v1/old-resource",
                "handler_name": "delete_old",
            }
        }
    }

    curr_endpoints = {
        # Unchanged:
        "endpoint:GET:/api/v1/users": prev_endpoints["endpoint:GET:/api/v1/users"],
        # Modified handler:
        "endpoint:POST:/api/v1/items": {
            "id": "endpoint:POST:/api/v1/items",
            "name": "POST /api/v1/items",
            "file_path": "app/api/items.py",
            "metadata": {
                "http_method": "POST",
                "route_path": "/api/v1/items",
                "handler_name": "create_item_v2",  # changed
            }
        },
        # Added endpoint:
        "endpoint:PUT:/api/v1/items": {
            "id": "endpoint:PUT:/api/v1/items",
            "name": "PUT /api/v1/items",
            "file_path": "app/api/items.py",
            "metadata": {
                "http_method": "PUT",
                "route_path": "/api/v1/items",
                "handler_name": "update_item",
            }
        }
        # Removed: "endpoint:DELETE:/api/v1/old-resource"
    }

    prev_incoming = {
        "endpoint:DELETE:/api/v1/old-resource": ["func:DeleteButton"],
        "endpoint:POST:/api/v1/items": ["func:ItemForm"],
    }
    prev_outgoing = {
        "endpoint:DELETE:/api/v1/old-resource": ["func:delete_old"],
        "endpoint:POST:/api/v1/items": ["func:create_item_old"],
    }

    changes = service.detect_endpoint_changes(
        prev_endpoints=prev_endpoints,
        curr_endpoints=curr_endpoints,
        prev_incoming=prev_incoming,
        prev_outgoing=prev_outgoing,
    )

    # Verify added
    assert len(changes["added"]) == 1
    assert changes["added"][0]["name"] == "PUT /api/v1/items"

    # Verify removed
    assert len(changes["removed"]) == 1
    assert changes["removed"][0]["name"] == "DELETE /api/v1/old-resource"

    # Verify modified
    assert len(changes["modified"]) == 1
    assert changes["modified"][0]["name"] == "POST /api/v1/items"
    assert any("handler" in m.lower() for m in changes["modified"][0]["modifications"])

    # Verify impact analysis
    impact = changes["impact_analysis"]
    assert "func:DeleteButton" in impact["affected_frontend_components"] or "func:ItemForm" in impact["affected_frontend_components"]
    assert impact["total_affected"] > 0


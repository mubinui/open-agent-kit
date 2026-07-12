"""Tests for the auxiliary attachment fields on topology AgentNode."""

from src.config.topology_models import AgentNode, TopologyConfig
from src.config.workflow_models import WorkflowConfig


def test_agent_node_accepts_aux_attachment_fields() -> None:
    node = AgentNode(
        id="n1",
        agent_id="agent_one",
        tools=["gmail_send", "db_query"],
        memory=True,
        knowledge=True,
    )
    assert node.tools == ["gmail_send", "db_query"]
    assert node.memory is True
    assert node.knowledge is True


def test_agent_node_defaults_preserve_legacy_configs() -> None:
    """Entries in existing workflows.json (no aux fields) must still validate."""
    node = AgentNode.model_validate({"id": "n1", "agent_id": "agent_one"})
    assert node.tools == []
    assert node.memory is None
    assert node.knowledge is None


def test_aux_fields_round_trip_through_workflow_config() -> None:
    workflow = WorkflowConfig(
        id="wf1",
        name="WF",
        description="test workflow",
        topology={
            "type": "sequential",
            "entry_node": "n1",
            "nodes": [
                {"id": "n1", "agent_id": "agent_one", "tools": ["gmail_send"], "memory": True},
                {"id": "n2", "agent_id": "agent_two", "knowledge": True},
            ],
            "edges": [{"from_node": "n1", "to_node": "n2"}],
        },
    )
    dumped = workflow.model_dump(mode="json")
    reloaded = WorkflowConfig(**dumped)
    n1, n2 = reloaded.topology.nodes
    assert n1.tools == ["gmail_send"]
    assert n1.memory is True
    assert n1.knowledge is None
    assert n2.knowledge is True
    assert n2.tools == []


def test_topology_validation_still_passes_with_aux_fields() -> None:
    topology = TopologyConfig(
        type="sequential",
        entry_node="n1",
        nodes=[
            AgentNode(id="n1", agent_id="agent_one", memory=True),
            AgentNode(id="n2", agent_id="agent_two", tools=["t1"]),
        ],
        edges=[{"from_node": "n1", "to_node": "n2"}],
    )
    assert topology.validate_topology() == []

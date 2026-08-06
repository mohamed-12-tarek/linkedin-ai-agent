import uuid

import pytest
from pydantic import ValidationError

from app.workflows.config import EdgeConfig, NodeConfig, WorkflowConfig
from app.workflows.context import ExecutionContext
from app.workflows.prompts import PromptEngine, PromptRenderError, PromptTemplate
from app.workflows.registry import GraphRegistry, NodeRegistry, RegistryError
from app.workflows.styles import HashtagStyle, StyleEngine, StyleProfile, Tone
from app.workflows.types import ModelRole


def make_context(**kwargs) -> ExecutionContext:
    return ExecutionContext(
        user_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        workflow_name="test.workflow",
        workflow_version="1.0.0",
        **kwargs,
    )


def test_style_engine_merges_structured_overrides_and_renders_rules() -> None:
    engine = StyleEngine()
    base = StyleProfile(name="Professional", preferred_terms=("practical",))

    style = engine.merge(
        base,
        {
            "tone": Tone.CONVERSATIONAL,
            "emoji": {"enabled": False},
            "formatting": {"use_bullets": True},
        },
    )

    assert style.tone is Tone.CONVERSATIONAL
    assert style.emoji.enabled is False
    assert style.formatting.use_bullets is True
    instructions = engine.render_instructions(style)
    assert "Do not use emojis." in instructions
    assert "Prefer these terms: practical." in instructions
    assert "Open with a concise, relevant hook." in instructions
    assert "Close with a clear call to action." in instructions


def test_style_profile_rejects_invalid_hashtag_range() -> None:
    with pytest.raises(ValidationError, match="minimum_count cannot exceed maximum_count"):
        HashtagStyle(minimum_count=6, maximum_count=2)


def test_prompt_engine_combines_template_style_variables_and_context() -> None:
    style = StyleProfile(name="Expert", tone=Tone.AUTHORITATIVE)
    context = make_context(style=style, variables={"audience": "engineers"})
    template = PromptTemplate(
        name="review",
        system_template="Workflow {workflow_name}. {style_instructions}",
        user_template="Review {topic} for {audience}.",
        required_variables=frozenset({"topic"}),
        output_instructions="Return valid JSON.",
    )

    rendered = PromptEngine(StyleEngine()).render(template, {"topic": "AI"}, context)

    assert "Tone: authoritative." in rendered.system
    assert rendered.user == "Review AI for engineers.\n\nOutput requirements:\nReturn valid JSON."
    assert rendered.variables["execution_id"] == str(context.execution_id)
    with pytest.raises(TypeError):
        rendered.variables["topic"] = "changed"


def test_prompt_engine_reports_all_missing_variables() -> None:
    template = PromptTemplate(
        name="missing",
        system_template="Use {style_instructions}",
        user_template="Write about {topic} for {audience}",
    )

    with pytest.raises(PromptRenderError, match="audience, topic"):
        PromptEngine(StyleEngine()).render(template, {}, make_context())


def test_workflow_configuration_validates_topology() -> None:
    config = WorkflowConfig(
        name="test.workflow",
        version="1.0.0",
        nodes=(NodeConfig(id="writer", type="test", model_role=ModelRole.WRITER),),
        edges=(
            EdgeConfig(source="$start", target="writer"),
            EdgeConfig(source="writer", target="$end"),
        ),
    )

    assert config.nodes[0].model_role is ModelRole.WRITER

    with pytest.raises(ValidationError, match="unknown node"):
        WorkflowConfig(
            name="invalid.workflow",
            version="1.0.0",
            nodes=(NodeConfig(id="writer", type="test"),),
            edges=(
                EdgeConfig(source="$start", target="missing"),
                EdgeConfig(source="writer", target="$end"),
            ),
        )

    with pytest.raises(ValidationError, match="unreachable nodes: orphan"):
        WorkflowConfig(
            name="disconnected.workflow",
            version="1.0.0",
            nodes=(
                NodeConfig(id="writer", type="test"),
                NodeConfig(id="orphan", type="test"),
            ),
            edges=(
                EdgeConfig(source="$start", target="writer"),
                EdgeConfig(source="writer", target="$end"),
                EdgeConfig(source="orphan", target="$end"),
            ),
        )


def test_registries_reject_duplicates_and_resolve_semantic_latest() -> None:
    nodes = NodeRegistry()
    nodes.register("test", lambda config: object())
    with pytest.raises(RegistryError, match="already registered"):
        nodes.register("test", lambda config: object())

    graphs = GraphRegistry()
    workflow_v2 = type("Workflow", (), {"name": "demo", "version": "2.0.0"})()
    workflow_v10 = type("Workflow", (), {"name": "demo", "version": "10.0.0"})()
    graphs.register(workflow_v2)
    graphs.register(workflow_v10)

    assert graphs.get("demo") is workflow_v10


def test_execution_context_is_immutable_and_supports_model_roles() -> None:
    calls = []
    factory = type(
        "Factory",
        (),
        {"create_for_role": lambda self, user_id, role: calls.append((user_id, role)) or role},
    )()
    context = make_context(
        model_factory=factory,
        model_role_overrides={ModelRole.WRITER: "reviewer"},
        variables={"language": "en"},
    )

    assert context.create_model(ModelRole.WRITER) == "reviewer"
    assert calls == [(context.user_id, "reviewer")]
    with pytest.raises(TypeError):
        context.variables["language"] = "fr"

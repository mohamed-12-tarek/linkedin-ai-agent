from app.workflows.post_generation.config import POST_GENERATION_CONFIG
from app.workflows.post_generation.nodes import (
    ApprovalBoundaryNode,
    CTAOptimizerNode,
    FinalJudgeNode,
    GrammarCheckerNode,
    HookOptimizerNode,
    ImageGenerationNode,
    ImageReviewNode,
    PlannerNode,
    PublisherBoundaryNode,
    RejectionNode,
    ReviewerNode,
    TranslatorNode,
    WriterNode,
)
from app.workflows.post_generation.state import PostGenerationState
from app.workflows.registry import NodeRegistry


def build_post_generation_workflow(
    prompt_engine,
    checkpointer=None,
    image_providers=None,
    image_storage=None,
    image_provider_order=(),
):
    from app.workflows.workflow import WorkflowBuilder

    registry = NodeRegistry()
    registry.register("post.planner", lambda config: PlannerNode(config, prompt_engine))
    registry.register("post.writer", lambda config: WriterNode(config, prompt_engine))
    registry.register("post.reviewer", lambda config: ReviewerNode(config, prompt_engine))
    registry.register(
        "post.hook_optimizer", lambda config: HookOptimizerNode(config, prompt_engine)
    )
    registry.register("post.cta_optimizer", lambda config: CTAOptimizerNode(config, prompt_engine))
    registry.register(
        "post.grammar_checker", lambda config: GrammarCheckerNode(config, prompt_engine)
    )
    registry.register("post.final_judge", lambda config: FinalJudgeNode(config, prompt_engine))
    registry.register("post.translator", lambda config: TranslatorNode(config, prompt_engine))
    registry.register(
        "post.image_generation",
        lambda config: ImageGenerationNode(
            config,
            prompt_engine,
            image_providers,
            image_storage,
            image_provider_order,
        ),
    )
    registry.register("post.image_review", lambda config: ImageReviewNode(config, image_storage))
    registry.register("post.approval_boundary", ApprovalBoundaryNode)
    registry.register("post.publisher_boundary", PublisherBoundaryNode)
    registry.register("post.rejection", RejectionNode)
    return WorkflowBuilder(registry).build(
        POST_GENERATION_CONFIG, PostGenerationState, checkpointer=checkpointer
    )

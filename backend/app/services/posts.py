import uuid

from app.models import Post, PostVersion
from app.schemas.posts import PostGenerateRequest, PostRead
from app.workflows.context import ExecutionContext
from app.workflows.post_generation.config import POST_GENERATION_CONFIG
from app.workflows.post_generation.nodes import CTAOptimizerNode, HookOptimizerNode, WriterNode
from app.workflows.post_generation.state import PostGenerationState
from app.workflows.styles import StyleProfile, Tone


class PostNotFoundError(Exception):
    pass


class StyleNotFoundError(Exception):
    pass


class PostGenerationService:
    def __init__(
        self, repository, workflow, model_factory, prompt_engine, approval_service=None
    ) -> None:
        self.repository = repository
        self.workflow = workflow
        self.model_factory = model_factory
        self.prompt_engine = prompt_engine
        self.approval_service = approval_service

    def list_posts(self, user_id: uuid.UUID) -> list[PostRead]:
        return [PostRead.model_validate(post) for post in self.repository.list_for_user(user_id)]

    def get_post(self, user_id: uuid.UUID, post_id: uuid.UUID) -> PostRead:
        post = self.repository.get_for_user(user_id, post_id)
        if post is None:
            raise PostNotFoundError
        return PostRead.model_validate(post)

    def generate(self, user_id: uuid.UUID, data: PostGenerateRequest) -> PostRead:
        style = self._style_profile(user_id, data)
        execution_id = uuid.uuid4()
        context = ExecutionContext(
            user_id=user_id,
            execution_id=execution_id,
            workflow_name=self.workflow.name,
            workflow_version=self.workflow.version,
            model_factory=self.model_factory,
            style=style,
        )
        initial_state: PostGenerationState = {
            "execution_id": str(execution_id),
            "workflow_name": self.workflow.name,
            "input": data.model_dump(mode="json"),
            "topic": data.topic,
            "description": data.description,
            "objective": data.objective,
            "audience": data.audience,
            "language": data.language,
            "length": data.length,
            "cta_type": data.cta_type,
            "emoji_level": data.emoji_level,
            "hashtag_mode": data.hashtag_mode,
            "image_mode": data.image_mode,
            "image_upload_id": data.image_upload_id,
            "image_prompt": data.image_prompt,
            "completed_nodes": [],
            "errors": [],
            "revisions": [],
        }
        post = Post(
            user_id=user_id,
            style_id=data.style_id,
            topic=data.topic,
            description=data.description,
            objective=data.objective,
            audience=data.audience,
            language=data.language,
            tone=data.tone,
            length=data.length,
            cta_type=data.cta_type,
            emoji_level=data.emoji_level,
            hashtag_mode=data.hashtag_mode,
            content=None,
            hook=None,
            cta_text=None,
            hashtags=None,
            status="generating",
        )
        if self.approval_service is not None:
            try:
                self.repository.add_post(post)
                self.repository.session.commit()
                self.approval_service.start(user_id, post, initial_state, style)
            except Exception:
                self.repository.session.rollback()
                raise
            stored = self.repository.get_for_user(user_id, post.id)
            if stored is None:
                raise RuntimeError("Generated post could not be reloaded")
            return PostRead.model_validate(stored)
        result = self.workflow.invoke(initial_state, context)
        post.content = result["content"]
        post.hook = result.get("hook")
        post.cta_text = result.get("cta")
        post.hashtags = " ".join(result.get("hashtags", []))
        post.status = result.get("status", "awaiting_approval")
        try:
            self.repository.add_post(post)
            for number, revision in enumerate(result.get("revisions", []), start=1):
                self.repository.add_version(
                    PostVersion(
                        post_id=post.id,
                        version_number=number,
                        content=revision["content"],
                        created_by_node=revision["node"],
                    )
                )
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise
        stored = self.repository.get_for_user(user_id, post.id)
        if stored is None:
            raise RuntimeError("Generated post could not be reloaded")
        return PostRead.model_validate(stored)

    def rewrite(self, user_id: uuid.UUID, post_id: uuid.UUID) -> PostRead:
        post = self._get_post(user_id, post_id)
        state = self._state_from_post(post)
        state["plan"] = {
            "angle": "Rewrite the existing post with stronger clarity and impact",
            "outline": ["hook", "main insight", "supporting points", "call to action"],
            "key_points": [post.description],
            "hook_direction": post.hook or "Use a specific, relevant opening",
        }
        node = WriterNode(self._node_config("writer"), self.prompt_engine)
        update = node.invoke(state, self._context(user_id, post))
        return self._apply_revision(post, update, "rewrite")

    def regenerate_hook(self, user_id: uuid.UUID, post_id: uuid.UUID) -> PostRead:
        post = self._get_post(user_id, post_id)
        node = HookOptimizerNode(self._node_config("hook_optimizer"), self.prompt_engine)
        update = node.invoke(self._state_from_post(post), self._context(user_id, post))
        return self._apply_revision(post, update, "regenerate_hook")

    def regenerate_cta(self, user_id: uuid.UUID, post_id: uuid.UUID) -> PostRead:
        post = self._get_post(user_id, post_id)
        node = CTAOptimizerNode(self._node_config("cta_optimizer"), self.prompt_engine)
        update = node.invoke(self._state_from_post(post), self._context(user_id, post))
        return self._apply_revision(post, update, "regenerate_cta")

    def resume_action(
        self,
        user_id: uuid.UUID,
        post_id: uuid.UUID,
        action: str,
        external_event_id: str,
    ) -> PostRead:
        if self.approval_service is None:
            raise RuntimeError("Approval workflow is not configured")
        execution = self.approval_service.executions.get_active_for_post(user_id, post_id)
        if execution is None:
            raise PostNotFoundError
        self.approval_service.resume(execution.id, action, external_event_id)
        return self.get_post(user_id, post_id)

    def _get_post(self, user_id: uuid.UUID, post_id: uuid.UUID) -> Post:
        post = self.repository.get_for_user(user_id, post_id)
        if post is None:
            raise PostNotFoundError
        return post

    def _context(self, user_id: uuid.UUID, post: Post) -> ExecutionContext:
        data = PostGenerateRequest.model_validate(
            {
                "topic": post.topic,
                "description": post.description,
                "objective": post.objective,
                "audience": post.audience,
                "language": post.language,
                "tone": post.tone,
                "style_id": post.style_id,
                "length": post.length,
                "cta_type": post.cta_type,
                "emoji_level": post.emoji_level,
                "hashtag_mode": post.hashtag_mode,
                "image_mode": "none",
            }
        )
        return ExecutionContext(
            user_id=user_id,
            execution_id=uuid.uuid4(),
            workflow_name=self.workflow.name,
            workflow_version=self.workflow.version,
            model_factory=self.model_factory,
            style=self._style_profile(user_id, data),
        )

    @staticmethod
    def _state_from_post(post: Post) -> PostGenerationState:
        return {
            "topic": post.topic,
            "description": post.description,
            "objective": post.objective,
            "audience": post.audience,
            "language": post.language,
            "length": post.length,
            "cta_type": post.cta_type,
            "emoji_level": post.emoji_level,
            "hashtag_mode": post.hashtag_mode,
            "content": post.content or "",
            "hook": post.hook or "",
            "cta": post.cta_text or "",
            "hashtags": (post.hashtags or "").split(),
            "revisions": [],
            "completed_nodes": [],
            "errors": [],
        }

    @staticmethod
    def _node_config(node_id: str):
        return next(node for node in POST_GENERATION_CONFIG.nodes if node.id == node_id)

    def _apply_revision(self, post: Post, update: dict, action: str) -> PostRead:
        post.content = update["content"]
        if "hook" in update:
            post.hook = update["hook"]
        if "cta" in update:
            post.cta_text = update["cta"]
        version = PostVersion(
            post_id=post.id,
            version_number=self.repository.next_version_number(post.id),
            content=post.content,
            created_by_node=action,
        )
        try:
            self.repository.add_version(version)
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise
        stored = self.repository.get_for_user(post.user_id, post.id)
        if stored is None:
            raise RuntimeError("Updated post could not be reloaded")
        return PostRead.model_validate(stored)

    def _style_profile(self, user_id: uuid.UUID, data: PostGenerateRequest) -> StyleProfile:
        rules: tuple[str, ...] = ()
        name = data.tone.title()
        if data.style_id is not None:
            style = self.repository.get_style_for_user(user_id, data.style_id)
            if style is None:
                raise StyleNotFoundError
            name = style.name
            rules = tuple(
                rule.strip()
                for rule in (style.instructions, style.example_posts or "")
                if rule.strip()
            )
        try:
            tone = Tone(data.tone.lower())
        except ValueError:
            tone = Tone.PROFESSIONAL
            rules = (*rules, f"Use a {data.tone} tone.")
        return StyleProfile(name=name, tone=tone, custom_rules=rules)

from app.workflows.prompts import PromptTemplate

POST_PROMPTS = {
    "planner": PromptTemplate(
        name="post.planner",
        system_template=(
            "You are a LinkedIn content strategist. Build a focused content plan. "
            "Do not draft the post yet. {style_instructions}"
        ),
        user_template=(
            "Topic: {topic}\nDescription: {description}\nObjective: {objective}\n"
            "Audience: {audience}\nLanguage: {language}\nLength: {length}"
        ),
        output_instructions=(
            'Return JSON: {"angle": string, "outline": [string], '
            '"key_points": [string], "hook_direction": string}.'
        ),
    ),
    "writer": PromptTemplate(
        name="post.writer",
        system_template="You are an expert LinkedIn writer. {style_instructions}",
        user_template=(
            "Write the complete post in {language}. Topic: {topic}. Objective: {objective}. "
            "Audience: {audience}. Target length: {length}. CTA type: {cta_type}. "
            "Emoji level: {emoji_level}. Hashtag mode: {hashtag_mode}. Plan: {plan_json}"
        ),
        output_instructions='Return JSON only: {"content": string}.',
    ),
    "reviewer": PromptTemplate(
        name="post.reviewer",
        system_template=(
            "You are a rigorous LinkedIn editor. Improve clarity, credibility, relevance, "
            "and audience fit without inventing facts. {style_instructions}"
        ),
        user_template="Review and revise this post:\n\n{content}",
        output_instructions='Return JSON: {"content": string, "feedback": [string]}.',
    ),
    "hook_optimizer": PromptTemplate(
        name="post.hook_optimizer",
        system_template=(
            "You optimize LinkedIn opening hooks. Keep the claim truthful and aligned with "
            "the post. {style_instructions}"
        ),
        user_template="Improve only the opening hook and return the complete post:\n\n{content}",
        output_instructions='Return JSON: {"hook": string, "content": string}.',
    ),
    "cta_optimizer": PromptTemplate(
        name="post.cta_optimizer",
        system_template=(
            "You optimize LinkedIn calls to action. Make the CTA natural and specific. "
            "{style_instructions}"
        ),
        user_template=(
            "CTA type: {cta_type}. Improve the CTA and return the complete post:\n\n{content}"
        ),
        output_instructions='Return JSON: {"cta": string, "content": string}.',
    ),
    "grammar_checker": PromptTemplate(
        name="post.grammar_checker",
        system_template=(
            "You are a grammar and readability editor. Preserve meaning, voice, formatting, "
            "and language. {style_instructions}"
        ),
        user_template="Correct this {language} post:\n\n{content}",
        output_instructions='Return JSON: {"content": string, "corrections": [string]}.',
    ),
    "final_judge": PromptTemplate(
        name="post.final_judge",
        system_template=(
            "You are the final quality judge for LinkedIn content. Apply only essential final "
            "edits. Reject unsupported claims, weak structure, or policy-risk content. "
            "{style_instructions}"
        ),
        user_template=(
            "Evaluate this post for objective '{objective}' and audience '{audience}':\n\n"
            "{content}"
        ),
        output_instructions=(
            'Return JSON: {"approved": boolean, "score": number 0-100, '
            '"reasoning": string, "content": string, "hook": string, "cta": string, '
            '"hashtags": [string]}.'
        ),
    ),
    "translator": PromptTemplate(
        name="post.translator",
        system_template=(
            "You translate LinkedIn content while preserving meaning, formatting, hook, CTA, "
            "and style. {style_instructions}"
        ),
        user_template="Translate this post into {target_language}:\n\n{content}",
        output_instructions='Return JSON: {"content": string, "language": string}.',
    ),
}

# ERD — AI LinkedIn Content Agent (Free-Tier Stack)

Database: PostgreSQL (free via Supabase Free Tier / Neon.tech Free Tier / local Docker)

## Mermaid ERD

```mermaid
erDiagram
    USERS ||--o{ PROMPTS : owns
    USERS ||--o{ STYLES : owns
    USERS ||--o{ POSTS : creates
    USERS ||--o{ CV_DOCUMENTS : uploads
    USERS ||--o{ LINKEDIN_ACCOUNTS : connects
    USERS ||--o{ JOB_MATCHES : receives
    USERS ||--o{ PROFILE_OPTIMIZATIONS : receives
    USERS ||--|| SETTINGS : has
    USERS ||--o{ LLM_MODELS : registers

    LLM_MODELS ||--o{ POSTS : "used_in (writer/reviewer/judge)"

    STYLES ||--o{ POSTS : applied_to

    POSTS ||--o{ POST_VERSIONS : has
    POSTS ||--o{ IMAGES : has
    POSTS ||--o{ TELEGRAM_MESSAGES : notifies
    POSTS ||--o| SCHEDULES : scheduled_as
    POSTS ||--o{ PUBLISH_HISTORY : published_as

    CV_DOCUMENTS ||--o{ JOB_MATCHES : matched_against

    JOB_LISTINGS ||--o{ JOB_MATCHES : matched_in

    USERS {
        uuid id PK
        string email
        string password_hash
        string telegram_chat_id
        timestamp created_at
    }

    LLM_MODELS {
        uuid id PK
        uuid user_id FK
        string name
        string provider
        string api_key_encrypted
        string base_url
        int context_length
        float cost_per_1k
        float temperature
        int max_tokens
        string role_type
        bool is_available
    }

    PROMPTS {
        uuid id PK
        uuid user_id FK
        string agent_type
        string name
        text content
        bool is_default
        timestamp created_at
    }

    STYLES {
        uuid id PK
        uuid user_id FK
        string name
        string type
        text instructions
        text example_posts
        bool is_public
        timestamp created_at
    }

    POSTS {
        uuid id PK
        uuid user_id FK
        uuid style_id FK
        string topic
        text description
        string objective
        string audience
        string language
        string tone
        string length
        string cta_type
        string emoji_level
        string hashtag_mode
        text content
        text hook
        text cta_text
        text hashtags
        string status
        timestamp created_at
        timestamp updated_at
    }

    POST_VERSIONS {
        uuid id PK
        uuid post_id FK
        int version_number
        text content
        string created_by_node
        timestamp created_at
    }

    IMAGES {
        uuid id PK
        uuid post_id FK
        string source
        text prompt_used
        string model_used
        string url
        bool is_selected
        timestamp created_at
    }

    TELEGRAM_MESSAGES {
        uuid id PK
        uuid post_id FK
        string telegram_message_id
        string action_taken
        timestamp sent_at
        timestamp action_at
    }

    SCHEDULES {
        uuid id PK
        uuid post_id FK
        timestamp scheduled_time
        string recurrence
        string status
    }

    LINKEDIN_ACCOUNTS {
        uuid id PK
        uuid user_id FK
        string access_token_encrypted
        string refresh_token_encrypted
        timestamp expires_at
        string profile_urn
    }

    PUBLISH_HISTORY {
        uuid id PK
        uuid post_id FK
        string linkedin_post_id
        string status
        timestamp published_at
    }

    PROFILE_OPTIMIZATIONS {
        uuid id PK
        uuid user_id FK
        text profile_snapshot
        text suggestions
        string status
        timestamp created_at
    }

    CV_DOCUMENTS {
        uuid id PK
        uuid user_id FK
        string file_path
        text parsed_text
        bool is_active
        timestamp uploaded_at
    }

    JOB_LISTINGS {
        uuid id PK
        string source
        string external_id
        string title
        string company
        text description
        string url
        string location
        timestamp fetched_at
    }

    JOB_MATCHES {
        uuid id PK
        uuid user_id FK
        uuid cv_id FK
        uuid job_listing_id FK
        float match_score
        text match_reasoning
        bool notified
        timestamp created_at
    }

    SETTINGS {
        uuid id PK
        uuid user_id FK
        string default_language
        string default_tone
        uuid default_style_id
        text default_models_json
        text image_settings_json
        text scheduling_settings_json
        text job_matching_settings_json
    }
```

## Design Notes

- **users**: Built from day one to support a future multi-tenant SaaS, even though the system will initially run for a single user.
- **llm_models**: Allows registering multiple models, each with a different `role_type` (writer, reviewer, judge, image, translation) — this is what enables Multi-Model Support.
- **post_versions**: Logs every Rewrite/Regenerate action so you can roll back to a previous version or track how a post evolved.
- **cv_documents + job_listings + job_matches**: The tables powering the job-matching feature — support multiple CVs, and store each match's score and reasoning (for transparency) plus notification status.
- **profile_optimizations**: Stores every time the system analyzed the profile and suggested improvements, along with the snapshot of text that was analyzed.
- **settings**: A 1-to-1 relationship with each user, holding job-matching settings (notification frequency, target keywords, target job title, etc.).

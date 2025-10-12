-- ============================================================================
-- INSIGHT #1: Communication Basics (FREE) - FINAL VERSION
-- ============================================================================

INSERT INTO insight_types (
    id,
    name,
    display_title,
    description,
    icon,
    is_premium,
    credit_cost,
    prompt_template,
    rag_query_keywords,
    response_schema,
    required_metadata_fields,
    is_active,
    created_at
) VALUES (
    gen_random_uuid(),
    'communication_basics',
    'Communication Basics',
    'Discover who starts conversations more, response time patterns, and how balanced your communication is. Get a quick health check of your chat dynamics.',
    '💬',
    false,
    1,
    
    -- PROMPT TEMPLATE (with placeholders for injection)
    'You are an empathetic relationship communication expert analyzing a romantic chat conversation.

**Chat Context:**
- User: {user_name}
- Partner: {partner_name}
- Chat: {chat_title}

**Chat Statistics:**
{metadata}

**Relevant Conversation Excerpts (Total: {total_chunks} chunks):**
{chunks}

**Your Task:**
Analyze the communication patterns in this romantic relationship. The messages may be in English, Hindi, or Hinglish (Hindi-English code-mixed text).

Provide insights on:
1. **Initiation Balance**: Who starts conversations more often? Calculate percentages for each person based on the metadata.
2. **Response Time Patterns**: Based on the metadata, describe each person''s typical response time in a warm, non-judgmental way.
3. **Conversation Balance**: Rate the overall balance of communication (0-10 scale). Consider message counts, initiation rates, and engagement.
4. **Communication Strengths**: Identify 2-3 positive patterns you observe in their conversations. Provide specific message examples as evidence.
5. **Gentle Tips**: 2 actionable, positive suggestions to enhance their communication.

**Important Guidelines:**
- Be warm, encouraging, and growth-oriented
- Never blame or criticize either person
- Frame everything as opportunities for growth
- For communication strengths, include actual message quotes as evidence (with speaker name and chunk index)
- Use their actual names ({user_name} and {partner_name}) when referring to them
- Keep language simple and relatable for Indian audience (ages 18-35)
- If response times are slow, frame it neutrally (e.g., "takes time to respond, likely busy")
- Celebrate their strengths prominently

**Output Format:**
Return your analysis as JSON matching the provided schema. Include evidence with actual message quotes.',

    -- RAG QUERY KEYWORDS (for vector search)
    'conversation starters, greetings, good morning, good night, how are you, checking in, initiation, first message, reaching out, daily chat, regular communication, texting patterns, responsiveness',
    
    -- RESPONSE SCHEMA (Gemini structured output format)
    '{
        "type": "object",
        "properties": {
            "initiation_balance": {
                "type": "object",
                "properties": {
                    "user_percentage": {
                        "type": "number",
                        "description": "Percentage of conversations initiated by user (0-100)"
                    },
                    "partner_percentage": {
                        "type": "number",
                        "description": "Percentage of conversations initiated by partner (0-100)"
                    },
                    "interpretation": {
                        "type": "string",
                        "description": "Warm, positive interpretation of what this balance means (2-3 sentences). Use actual names."
                    }
                },
                "required": ["user_percentage", "partner_percentage", "interpretation"]
            },
            "response_time_patterns": {
                "type": "object",
                "properties": {
                    "user_pattern": {
                        "type": "string",
                        "description": "Description of user''s typical response time in friendly language (e.g., responds within minutes, very attentive)"
                    },
                    "partner_pattern": {
                        "type": "string",
                        "description": "Description of partner''s typical response time in friendly language"
                    },
                    "compatibility_insight": {
                        "type": "string",
                        "description": "How well their response styles work together. Frame positively. (2-3 sentences)"
                    }
                },
                "required": ["user_pattern", "partner_pattern", "compatibility_insight"]
            },
            "conversation_balance_score": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer",
                        "description": "Overall balance score from 0-10 (10 = perfectly balanced). Consider initiation, message counts, and engagement.",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "explanation": {
                        "type": "string",
                        "description": "What this score means for their relationship. Be encouraging. (2-3 sentences)"
                    }
                },
                "required": ["score", "explanation"]
            },
            "communication_strengths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "strength": {
                            "type": "string",
                            "description": "Name of the positive pattern (e.g., Consistent Check-ins, Playful Banter, Emotional Support)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Explain what makes this a strength (2-3 sentences)"
                        },
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "Exact message text from the chat"
                                    },
                                    "speaker": {
                                        "type": "string",
                                        "description": "Name of the person who sent this message"
                                    },
                                    "chunk_index": {
                                        "type": "integer",
                                        "description": "Index of the chunk this message came from (0-based)"
                                    }
                                },
                                "required": ["message", "speaker", "chunk_index"]
                            },
                            "minItems": 1,
                            "maxItems": 3,
                            "description": "1-3 actual message examples supporting this strength"
                        }
                    },
                    "required": ["strength", "description", "evidence"]
                },
                "minItems": 2,
                "maxItems": 3,
                "description": "2-3 positive communication patterns with evidence"
            },
            "gentle_tips": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "tip": {
                            "type": "string",
                            "description": "Actionable suggestion in simple language"
                        },
                        "why_it_helps": {
                            "type": "string",
                            "description": "Brief explanation of the benefit (1-2 sentences)"
                        },
                        "example": {
                            "type": "string",
                            "description": "A concrete example or conversation starter they could try"
                        }
                    },
                    "required": ["tip", "why_it_helps", "example"]
                },
                "minItems": 2,
                "maxItems": 2,
                "description": "Two positive, actionable communication tips"
            },
            "overall_summary": {
                "type": "string",
                "description": "A warm, encouraging 2-3 sentence summary of their communication dynamic. Highlight what''s working well."
            }
        },
        "required": ["initiation_balance", "response_time_patterns", "conversation_balance_score", "communication_strengths", "gentle_tips", "overall_summary"]
    }',
    
    -- REQUIRED METADATA FIELDS (what to extract from chat_metadata)
    '["total_messages", "total_days", "messages_per_day_avg", "user_stats"]',
    
    true,  -- is_active
    NOW()
);

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

-- SELECT 
--     name,
--     display_title,
--     is_premium,
--     icon,
--     LENGTH(prompt_template) as prompt_length,
--     LENGTH(rag_query_keywords) as keywords_length,
--     jsonb_pretty(response_schema) as schema_preview,
--     required_metadata_fields
-- FROM insight_types 
-- WHERE name = 'communication_basics';


-- -- 1. Conflict Resolution Style Insight Type (Corrected)
-- INSERT INTO insight_types (id, name, display_title, description, icon, prompt_template, is_premium, credit_cost, is_active)
-- VALUES (
--     gen_random_uuid(), -- Ensures a new UUID is generated by the database
--     'conflict_analysis',
--     'Conflict Resolution Style',
--     'Analyzes how conflicts are initiated, handled, and resolved, identifying destructive or constructive patterns.',
--     '💥',
--     'You are a relationship expert. Analyze the conversation history provided below for conflict resolution patterns. Identify the style of each participant (e.g., accommodating, competing, compromising, avoiding, collaborating) and provide a summary of your findings in JSON format.',
--     FALSE,
--     1,
--     TRUE
-- );

-- -- 2. Communication Style & Tone Insight Type (Corrected)
-- INSERT INTO insight_types (id, name, display_title, description, icon, prompt_template, is_premium, credit_cost, is_active)
-- VALUES (
--     gen_random_uuid(), -- Ensures a new UUID is generated by the database
--     'communication_patterns',
--     'Communication Style & Tone',
--     'Evaluates the overall tone, politeness, and active listening skills displayed by the users in the conversation.',
--     '🗣️',
--     'Analyze the conversation for communication patterns. Focus on identifying tone (positive, negative, neutral), the use of "I" vs "You" statements, and evidence of active listening. Generate a report in JSON format summarizing the distinct communication style of each party.',
--     TRUE, -- Example of a premium insight
--     3,
--     TRUE
-- );

-- -- 3. Relationship Health & Indicators Insight Type (Corrected)
-- INSERT INTO insight_types (id, name, display_title, description, icon, prompt_template, is_premium, credit_cost, is_active)
-- VALUES (
--     gen_random_uuid(), -- Ensures a new UUID is generated by the database
--     'relationship_indicators',
--     'Relationship Health & Indicators',
--     'Highlights positive "Green Flags" (e.g., support, validation) and potential "Red Flags" (e.g., stonewalling, criticism) in the conversation.',
--     '🚦',
--     'Search the provided chat log for both Green Flags (supportive, affirming, appreciative language) and Red Flags (dismissive, controlling, critical language). List the top 3 of each category with a supporting quote from the chat in a structured JSON object.',
--     FALSE,
--     1,
--     TRUE
-- );
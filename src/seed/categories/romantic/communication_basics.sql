-- INSIGHT TYPE: Communication Basics
-- Supports: 1-on-1 AND Group Chats (2+ participants)
-- Cost: 50 coins
-- Treats all participants equally (no user vs partner bias)

INSERT INTO insight_types (
    id,
    name,
    display_title,
    description,
    icon,
    prompt_template,
    rag_query_keywords,
    response_schema,
    required_metadata_fields,
    is_premium,
    credit_cost,
    supports_group_chats,
    max_participants,
    is_active
) VALUES (
    gen_random_uuid(),
    'communication_basics',
    'Communication Basics',
    'See who starts conversations, response patterns, and how balanced communication is across all participants.',
    '💬',
    
    -- PROMPT TEMPLATE --
    'You are analyzing communication patterns in a chat conversation.

**Chat Details:**
- Total Participants: {participant_count}
- Participant Names: {participant_list}

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze communication health across all participants. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use all participants'' names equally - treat everyone fairly with no bias
- **Evidence Format:** Provide exact message quotes with timestamps in format [DD/MM/YY, HH:MM:SS AM/PM]
- **Evidence Quality:** Show interaction between participants, not isolated messages
- **Focus:** Emphasize patterns and growth opportunities, not problems

Provide insights on:

1. **Initiation Balance**: 
   - For EACH participant, calculate % of conversations they initiated (use conversation_initiations from metadata)
   - Assess if distribution is balanced or if some dominate
   - For 2 people: Compare directly. For 3+: Identify most active/quiet

2. **Response Patterns**: 
   - For EACH participant, describe their typical response time (use avg_response_time_seconds)
   - Who responds fastest? Who takes time?
   - Frame neutrally - "takes time" not "slow"

3. **Message Contribution**: 
   - For EACH participant: % of total messages and % of total words
   - Who contributes most/least to conversations?
   - Calculate if word_count vs message_count shows verbose vs concise styles

4. **Engagement Indicators**:
   - For EACH participant: questions asked, double texting rate
   - Who shows most curiosity (questions)?
   - Interpret double-texting (enthusiasm vs over-eagerness based on context)

5. **Communication Strengths**: 
   - Find 2-3 positive patterns across ALL participants
   - Examples: consistent check-ins, supportive responses, playful banter, good back-and-forth
   - Provide EXACT message quotes with timestamps as evidence
   - Must show interaction between participants (not isolated messages)

6. **Balance Recommendations**: 
   - 2 specific tips to improve overall communication balance
   - Base on actual data (e.g., if one person dominates, suggest others initiate more)
   - Positive framing only - opportunities, not criticisms

**INTERPRETATION GUIDELINES:**
- For 2 people: Use "between X and Y" language for direct comparison
- For 3+: Use group language like "In this group", "among all participants"
- Frame differences neutrally - "takes time to respond" not "slow responder"
- Keep language simple and accessible for Indian audience (18-35)
- Always end on a positive, constructive note

**Output:** Return JSON matching the provided schema.',

    -- RAG QUERY KEYWORDS --
    'greetings, good morning, good night, hey, hi, hello, how are you, checking in, conversation starters, asking questions, supportive messages, back and forth, replies, responses',

    -- RESPONSE SCHEMA --
    '{
      "type": "object",
      "required": [
        "initiation_balance",
        "response_patterns",
        "message_contribution",
        "engagement_indicators",
        "communication_strengths",
        "balance_recommendations",
        "overall_health_assessment"
      ],
      "properties": {
        "initiation_balance": {
          "type": "object",
          "required": ["participants", "balance_assessment"],
          "properties": {
            "participants": {
              "type": "array",
              "minItems": 2,
              "items": {
                "type": "object",
                "required": ["name", "initiation_count", "percentage"],
                "properties": {
                  "name": {"type": "string"},
                  "initiation_count": {"type": "integer"},
                  "percentage": {
                    "type": "number",
                    "description": "Percentage of conversations this person started (0-100)"
                  }
                }
              }
            },
            "balance_assessment": {
              "type": "object",
              "required": ["rating", "interpretation"],
              "properties": {
                "rating": {
                  "type": "string",
                  "enum": ["balanced", "slightly_imbalanced", "highly_imbalanced"],
                  "description": "balanced: all within 10% of equal split, slightly: 10-25% difference, highly: >25%"
                },
                "interpretation": {
                  "type": "string",
                  "description": "3-4 sentences. For 2 people: compare directly. For groups: note who dominates/is quiet. Use names. Be encouraging."
                }
              }
            }
          }
        },
        "response_patterns": {
          "type": "object",
          "required": ["participants", "compatibility_note"],
          "properties": {
            "participants": {
              "type": "array",
              "minItems": 2,
              "items": {
                "type": "object",
                "required": ["name", "avg_response_seconds", "response_style"],
                "properties": {
                  "name": {"type": "string"},
                  "avg_response_seconds": {
                    "type": "number",
                    "description": "From metadata"
                  },
                  "response_style": {
                    "type": "string",
                    "description": "Friendly description: instant responder, responds within hours, takes their time"
                  }
                }
              }
            },
            "compatibility_note": {
              "type": "string",
              "description": "2-3 sentences on how response styles work together. Frame positively."
            }
          }
        },
        "message_contribution": {
          "type": "object",
          "required": ["participants", "balance_note"],
          "properties": {
            "participants": {
              "type": "array",
              "minItems": 2,
              "items": {
                "type": "object",
                "required": ["name", "message_percentage", "word_percentage", "avg_words_per_message", "style"],
                "properties": {
                  "name": {"type": "string"},
                  "message_percentage": {
                    "type": "number",
                    "description": "% of total messages"
                  },
                  "word_percentage": {
                    "type": "number",
                    "description": "% of total words"
                  },
                  "avg_words_per_message": {
                    "type": "number",
                    "description": "From metadata"
                  },
                  "style": {
                    "type": "string",
                    "description": "concise, balanced, or verbose (based on words per message)"
                  }
                }
              }
            },
            "balance_note": {
              "type": "string",
              "description": "2-3 sentences. Is contribution balanced? Who drives conversations through volume?"
            }
          }
        },
        "engagement_indicators": {
          "type": "object",
          "required": ["participants", "engagement_insight"],
          "properties": {
            "participants": {
              "type": "array",
              "minItems": 2,
              "items": {
                "type": "object",
                "required": ["name", "questions_asked", "double_texting_rate"],
                "properties": {
                  "name": {"type": "string"},
                  "questions_asked": {
                    "type": "integer",
                    "description": "From metadata"
                  },
                  "double_texting_rate": {
                    "type": "number",
                    "description": "From metadata (percentage)"
                  }
                }
              }
            },
            "engagement_insight": {
              "type": "string",
              "description": "3-4 sentences analyzing curiosity (questions) and enthusiasm (double-texting). Who shows most interest? Nuanced interpretation."
            }
          }
        },
        "communication_strengths": {
          "type": "array",
          "minItems": 2,
          "maxItems": 3,
          "items": {
            "type": "object",
            "required": ["strength_title", "description", "evidence"],
            "properties": {
              "strength_title": {
                "type": "string",
                "description": "e.g., Daily Check-ins, Supportive Responses, Good Back-and-Forth"
              },
              "description": {
                "type": "string",
                "description": "2-3 sentences explaining this strength"
              },
              "evidence": {
                "type": "array",
                "minItems": 2,
                "maxItems": 5,
                "items": {
                  "type": "object",
                  "required": ["message", "speaker", "timestamp", "context"],
                  "properties": {
                    "message": {
                      "type": "string",
                      "description": "EXACT message text from chunk"
                    },
                    "speaker": {
                      "type": "string",
                      "description": "Name of sender"
                    },
                    "timestamp": {
                      "type": "string",
                      "description": "Format: [DD/MM/YY, HH:MM:SS AM/PM]"
                    },
                    "context": {
                      "type": "string",
                      "description": "Context of what is happening in this evidence chat"
                    }
                  }
                },
                "description": "2-5 messages showing interaction/pattern"
              }
            }
          }
        },
        "balance_recommendations": {
          "type": "array",
          "minItems": 2,
          "maxItems": 2,
          "items": {
            "type": "object",
            "required": ["recommendation_title", "target_participants", "suggestion", "why_it_helps", "example"],
            "properties": {
              "recommendation_title": {
                "type": "string",
                "description": "e.g., Balance Initiations, Ask More Questions"
              },
              "target_participants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of participants this applies to. Can be [all] or specific names."
              },
              "suggestion": {
                "type": "string",
                "description": "Specific actionable advice based on their data"
              },
              "why_it_helps": {
                "type": "string",
                "description": "1-2 sentences on benefit"
              },
              "example": {
                "type": "string",
                "description": "Concrete example or conversation starter"
              }
            }
          }
        },
        "overall_health_assessment": {
          "type": "object",
          "required": ["score", "rating", "summary"],
          "properties": {
            "score": {
              "type": "integer",
              "minimum": 0,
              "maximum": 10,
              "description": "Overall communication health (0-10). Consider balance, engagement, response patterns."
            },
            "rating": {
              "type": "string",
              "enum": ["excellent", "good", "needs_improvement"],
              "description": "excellent: 8-10, good: 5-7, needs_improvement: 0-4"
            },
            "summary": {
              "type": "string",
              "description": "Warm 3-4 sentence summary. Highlight strengths, gently note growth areas. End encouragingly."
            }
          }
        }
      }
    }'::jsonb,

    -- REQUIRED METADATA FIELDS --
    '["total_messages", "total_days", "messages_per_day_avg", "user_stats"]'::jsonb,

    -- CONFIG --
    true,  -- is_premium
    50,    -- credit_cost
    true,  -- supports_group_chats (NOW TRUE)
    NULL,  -- max_participants (NULL = unlimited)
    true   -- is_active
);
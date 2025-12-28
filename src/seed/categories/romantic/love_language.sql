INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'f7b8c3d4-2e5f-4a6b-9c8d-1e2f3a4b5c6d'::uuid,
  'love_language',
  'Love Language & Appreciation',
  'Discover how you each express love and appreciation, and learn to speak each other''s language better.',
  '💝',
  'You are analyzing love language patterns in a romantic relationship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Identify love languages based on the 5 types: Words of Affirmation, Acts of Service, Receiving Gifts, Quality Time, Physical Touch (adapted for text). Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally - treat partners fairly with no bias
- **Evidence Format:** Provide exact message quotes with timestamps in appropriate format
- **Evidence Quality:** Show meaningful interactions, not isolated messages
- **Focus:** Emphasize patterns and growth opportunities, not problems

Provide insights on:

1. **Primary Love Language per Person**:
   - For EACH person: What is their PRIMARY way of expressing love?
   - Look for patterns in their messages:
     * Words of Affirmation: compliments, encouragement, "I''m proud of you", "You''re amazing"
     * Acts of Service: offering help, "Let me do that for you", problem-solving, taking care of tasks
     * Quality Time: wanting to talk, "miss talking to you", sharing experiences, deep conversations
     * Gifts (adapted): sharing photos, links, songs, memories, "this reminded me of you"
     * Physical Touch (adapted): emojis (hearts, hugs, kisses), "wish I could hug you", references to physical affection
   - Rate confidence: high, medium, low
   - Provide 3-4 evidence messages showing this language

2. **Secondary Love Language**:
   - For EACH person: What is their SECONDARY expression?
   - May be close in frequency to primary
   - Provide 2-3 evidence messages

3. **Appreciation Expression**:
   - How does each person say "thank you" or show gratitude?
   - Examples: verbal thanks, reciprocal actions, emojis, gifts
   - Who expresses appreciation more frequently?
   - Provide 3-4 evidence messages

4. **Recognition of Effort**:
   - Do they notice and acknowledge each other''s efforts?
   - Examples: "Thank you for...", "I noticed that...", "That means a lot"
   - Who is better at recognizing effort?
   - Provide 2-3 evidence exchanges

5. **Language Compatibility**:
   - Do their primary languages match or differ?
   - If different: Are they adapting to each other''s language?
   - Look for evidence of learning (e.g., if partner needs words of affirmation, do they give more compliments over time?)
   - 3-4 sentences analysis

6. **Missing Love Languages**:
   - Which love languages are UNDERUSED in this relationship?
   - This is an opportunity for growth
   - Be specific about what''s missing

7. **Beautiful Moments**:
   - Find 2-3 examples where one person perfectly spoke the other''s love language
   - Moments of deep appreciation or recognition
   - Must show both people in the exchange
   - Provide evidence with context

8. **Recommendations**:
   - 2 specific suggestions to better express love in partner''s language
   - Base on actual data (e.g., if partner is Quality Time but conversations are short, suggest deeper check-ins)
   - Include example messages to send

**INTERPRETATION GUIDELINES:**
- Recognize cultural adaptations (Indian couples may express differently)
- If data is limited for a language, say "Not clearly evident from messages"
- Focus on TEXT-BASED expressions (we can''t know offline actions)

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'thank you, grateful, appreciate, love you, miss you, proud of you, amazing, beautiful, you are, compliment, help, let me, for you, reminded me, sharing, sending, photo, song, talk to you, conversation, time together, hug, kiss, heart, emoji, thinking of you',
  '{
  "type": "object",
  "required": [
    "primary_languages",
    "secondary_languages",
    "appreciation",
    "recognition",
    "compatibility",
    "missing_languages",
    "beautiful_moments",
    "recommendations",
    "overall"
  ],
  "properties": {
    "primary_languages": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "language", "confidence", "description", "evidence"],
            "properties": {
              "name": {"type": "string"},
              "language": {"type": "string"},
              "confidence": {"type": "string"},
              "description": {"type": "string"},
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["message", "speaker", "timestamp"],
                  "properties": {
                    "message": {"type": "string"},
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "context": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "secondary_languages": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "language", "description", "evidence"],
            "properties": {
              "name": {"type": "string"},
              "language": {"type": "string"},
              "description": {"type": "string"},
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["message", "speaker", "timestamp"],
                  "properties": {
                    "message": {"type": "string"},
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "context": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "appreciation": {
      "type": "object",
      "required": ["participants", "frequency_comparison", "evidence"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "expression_style", "frequency"],
            "properties": {
              "name": {"type": "string"},
              "expression_style": {"type": "string"},
              "frequency": {"type": "string"}
            }
          }
        },
        "frequency_comparison": {"type": "string"},
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["message", "speaker", "timestamp", "appreciation_type"],
            "properties": {
              "message": {"type": "string"},
              "speaker": {"type": "string"},
              "timestamp": {"type": "string"},
              "appreciation_type": {"type": "string"}
            }
          }
        }
      }
    },
    "recognition": {
      "type": "object",
      "required": ["analysis", "balance", "evidence"],
      "properties": {
        "analysis": {"type": "string"},
        "balance": {"type": "string"},
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["context", "exchange"],
            "properties": {
              "context": {"type": "string"},
              "exchange": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["message", "speaker", "timestamp"],
                  "properties": {
                    "message": {"type": "string"},
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "compatibility": {
      "type": "object",
      "required": ["match_type", "analysis", "adaptation_evidence"],
      "properties": {
        "match_type": {"type": "string"},
        "analysis": {"type": "string"},
        "adaptation_evidence": {"type": "string"}
      }
    },
    "missing_languages": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["language", "explanation"],
        "properties": {
          "language": {"type": "string"},
          "explanation": {"type": "string"}
        }
      }
    },
    "beautiful_moments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["moment_title", "description", "exchange"],
        "properties": {
          "moment_title": {"type": "string"},
          "description": {"type": "string"},
          "exchange": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["message", "speaker", "timestamp"],
              "properties": {
                "message": {"type": "string"},
                "speaker": {"type": "string"},
                "timestamp": {"type": "string"}
              }
            }
          }
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "target", "suggestion", "why", "example_messages"],
        "properties": {
          "title": {"type": "string"},
          "target": {"type": "array", "items": {"type": "string"}},
          "suggestion": {"type": "string"},
          "why": {"type": "string"},
          "example_messages": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "summary"],
      "properties": {
        "score": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "description": "Love language compatibility score (0-10)"
        },
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);

-- Link to romantic category
-- INSERT INTO public.category_insight_types
-- (id, category_id, insight_type_id, display_order, created_at)
-- VALUES(
--   gen_random_uuid(),
--   (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--   'f7b8c3d4-2e5f-4a6b-9c8d-1e2f3a4b5c6d'::uuid,
--   3,
--   NOW()
-- );
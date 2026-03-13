INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'c9d0e1f2-3a4b-5c6d-7e8f-9a0b1c2d3e4f'::uuid,
  'family_conflict_patterns',
  'Conflict & Tension Patterns',
  'Uncover how your family navigates disagreements, tension, and difficult conversations.',
  '🔥',
  'You are analyzing conflict and tension patterns in a family chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how this family handles tension, disagreements, and difficult conversations. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a compassionate family therapist - non-judgmental, culturally aware, and constructive
  * Family conflict is normal and healthy when handled well
  * AVOID dramatic labels: "toxic", "abusive", "dysfunctional" (unless clearly warranted)
  * Use careful language: "there''s tension around...", "disagreements tend to center on..."
  * Frame patterns as observable, not as accusations
- **Length:** Match to what''s actually visible - don''t invent conflict that isn''t there
- **Equal Treatment:** No one person is "the problem" - conflict is relational
- **Evidence:** Show actual exchanges; don''t extrapolate heavily from limited data
- **Sensitivity:** Family conflicts are deeply personal - handle with care

Provide insights on:

1. **Conflict Presence**:
   - Are there visible tensions or conflicts in this chat?
   - Rate: frequently tense, occasional tension, rare tension, mostly harmonious, no visible conflict
   - Is conflict expressed directly or indirectly?
   - 3-4 sentences honest assessment

2. **Family-Specific Conflict Patterns**:
   - Family conflicts have unique dynamics unlike other relationships. Look for:
     * Guilt-obligation cycles: "after everything I''ve done", "you don''t care about family"
     * Generational conflict: different values or expectations between generations
     * The "everything is fine" pattern: conflict avoided, issues swept under rug
     * Recurring themes: the same topic causes tension repeatedly
     * Triangulation: discussing problems about one person with another
     * Passive communication: hinting rather than saying things directly
   - Identify which patterns (if any) are visible with evidence

3. **Individual Conflict Styles** (Family Context):
   - For EACH person: how do they behave in family tension?
   - Family-specific styles:
     * The Appeaser: quickly smooths things over, avoids confrontation
     * The Authoritative: asserts their view as the correct one
     * The Guilt-tripper: appeals to sacrifice, obligation, or history
     * The Withdrawer: goes quiet, stops engaging, disappears from conversation
     * The Mediator: tries to calm and bridge between others
     * The Direct Confronter: addresses issues head-on
   - 1-2 evidence items per person showing their style

4. **Topics That Create Tension**:
   - What subjects or situations trigger friction?
   - Common family conflict topics: decisions about family matters, money/finances, life choices (career, relationship, lifestyle), expectations around duties, comparisons, privacy
   - For each identified topic: brief description and 1-2 evidence items

5. **How Conflict Resolves** (if visible):
   - Does conflict get resolved, or does it get dropped/suppressed?
   - Resolution approaches: direct acknowledgment, someone conceding, humor to defuse, topic change, third party intervention
   - If conflicts aren''t resolved in chat, note that they may happen offline

6. **What This Family Does Well in Disagreements**:
   - Even in tension: are there positive behaviors?
   - Look for: staying respectful, not bringing up old wounds, someone defusing tension, coming back to check on each other
   - 1-2 genuine positives with evidence

7. **Patterns Worth Addressing**:
   - 1-2 patterns that, if continued, might strain family connection
   - Be careful and constructive - these should feel like caring observations, not accusations
   - Include a reflection prompt rather than a verdict

8. **Recommendations**:
   - 2-3 gentle, specific suggestions for navigating family tension better
   - Include example phrases that feel natural in a family context

**INTERPRETATION GUIDELINES:**
- Family conflict is universal and normal - normalize it
- Indian families may have different norms around authority and disagreement - respect this
- Conflict avoidance is sometimes healthy (choosing your battles); not always a problem
- If there is little conflict visible, it might mean: genuinely harmonious, conflict handled offline, or avoidance - be honest about which seems likely
- Never make serious clinical diagnoses (narcissism, abuse, etc.) - if something seems serious, gently note they may benefit from professional support

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'not fair, always, never, you never, why do you, silent, avoid, angry, hurt, expectations, disappointed, obligated, after everything, don''t care, family, responsibility, pressure, guilt, upset, tense, argument, disagree, issue, problem, sensitive, difficult topic, avoid, ignore, fine, okay, whatever',
  '{
  "type": "object",
  "required": [
    "conflict_presence",
    "family_specific_patterns",
    "individual_styles",
    "tension_topics",
    "conflict_resolution",
    "positive_conflict_behaviors",
    "patterns_to_address",
    "recommendations",
    "overall"
  ],
  "properties": {
    "conflict_presence": {
      "type": "object",
      "required": ["level", "expression_style", "assessment"],
      "properties": {
        "level": {"type": "string"},
        "expression_style": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "family_specific_patterns": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pattern_name", "description"],
        "properties": {
          "pattern_name": {"type": "string"},
          "description": {"type": "string"},
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
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": {"type": "string"},
                      "message": {"type": "string"},
                      "timestamp": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "individual_styles": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "style", "description"],
            "properties": {
              "name": {"type": "string"},
              "style": {"type": "string"},
              "description": {"type": "string"},
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
                        "required": ["speaker", "message", "timestamp"],
                        "properties": {
                          "speaker": {"type": "string"},
                          "message": {"type": "string"},
                          "timestamp": {"type": "string"}
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "tension_topics": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["topic", "description"],
        "properties": {
          "topic": {"type": "string"},
          "description": {"type": "string"},
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
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": {"type": "string"},
                      "message": {"type": "string"},
                      "timestamp": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "conflict_resolution": {
      "type": "object",
      "required": ["approach", "effectiveness", "description"],
      "properties": {
        "approach": {"type": "string"},
        "effectiveness": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "positive_conflict_behaviors": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["behavior", "description"],
        "properties": {
          "behavior": {"type": "string"},
          "description": {"type": "string"},
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
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": {"type": "string"},
                      "message": {"type": "string"},
                      "timestamp": {"type": "string"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "patterns_to_address": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["pattern", "description", "reflection_prompt"],
        "properties": {
          "pattern": {"type": "string"},
          "description": {"type": "string"},
          "reflection_prompt": {"type": "string"}
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "target", "suggestion", "example_phrases"],
        "properties": {
          "title": {"type": "string"},
          "target": {
            "type": "array",
            "items": {"type": "string"}
          },
          "suggestion": {"type": "string"},
          "example_phrases": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "conflict_health", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "conflict_health": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'a9d8e7f6-5c4b-3a2d-1e0f-9a8b7c6d5e4f'::uuid,
  'conflict_resolution',
  'Conflict & Communication Under Stress',
  'Understand how you handle disagreements, stress, and difficult conversations - and learn to fight fair.',
  '⚖️',
  'You are analyzing conflict resolution and stress communication patterns in a romantic relationship.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Identify how this couple handles disagreements, tension, and stressful situations. Messages may be in English, Hindi, or Hinglish.

Provide insights on:

1. **Conflict Presence & Frequency**:
   - Are there visible conflicts/disagreements in the chat?
   - If yes: Approximate frequency (rare, occasional, frequent)
   - If no: Is this genuinely harmonious OR are conflicts avoided/taken offline?
   - Look for: arguments, tension, "but", "however", defensive language, hurt feelings
   - 3-4 sentences assessment

2. **Conflict Triggers**:
   - What topics/situations spark tension?
   - Common triggers: miscommunication, unmet expectations, time/attention, external stress, family/friends
   - For EACH identified trigger: provide 1-2 evidence exchanges
   - If no conflicts: state "No clear conflict triggers identified"

3. **Individual Conflict Styles**:
   - For EACH person: How do they behave during disagreements?
   - Styles to identify:
     * Avoidant: withdraws, goes silent, changes subject, "whatever", "fine"
     * Competitive: defensive, wants to win, raises counterpoints, "you always..."
     * Collaborative: seeks understanding, asks questions, "help me understand", compromises
     * Accommodating: quickly apologizes, gives in, prioritizes peace over resolution
     * Passive-aggressive: indirect criticism, sarcasm, subtle digs
   - Rate intensity: low, moderate, high
   - Provide description and evidence

4. **Communication Patterns Under Stress**:
   - How does communication change when stressed/upset?
   - Look for: message frequency changes, tone shifts, emoji usage drops, shorter messages, delayed responses
   - Do they communicate stress directly ("I''m stressed") or indirectly (behavior changes)?
   - Who initiates difficult conversations?
   - 3-4 sentences analysis

5. **Repair & Recovery**:
   - After tension, how do they reconnect?
   - Repair strategies: direct apology, humor, gifts/gestures, time/space then return, pretend nothing happened
   - Who initiates repair more often?
   - Timeframe: immediate, hours, days
   - Provide 2-3 evidence exchanges showing repair process

6. **Positive Conflict Behaviors**:
   - What do they do WELL during disagreements?
   - Examples: staying respectful, validating feelings, taking breaks, using "I feel" statements, humor to diffuse
   - Find 2-3 examples with evidence
   - Celebrate healthy patterns

7. **Destructive Patterns** (if any):
   - Red flags: name-calling, bringing up past, "you always/never", silent treatment >24hrs, threats
   - Be honest but gentle - frame as "areas to watch"
   - If none: celebrate this explicitly
   - Provide evidence if present

8. **Stress Support**:
   - When one person is stressed (external: work, family, health), how does partner respond?
   - Supportive responses vs adding pressure
   - Provide 2-3 examples

9. **Growth Recommendations**:
   - 2-3 specific suggestions to handle conflict more constructively
   - Base on actual patterns (e.g., if avoidant, suggest "I need time but let''s revisit in X hours")
   - Include conflict de-escalation techniques
   - Provide example phrases

**CRITICAL GUIDELINES:**
- Be extremely careful with interpretation - not every "but" is conflict
- Never catastrophize or pathologize normal couple disagreements
- If conflicts are healthy/minor, celebrate this (most couples fight!)
- Frame destructive patterns as "opportunities" not "problems"
- Some couples genuinely don''t fight in text - acknowledge this
- Cultural context: Indian couples may handle conflict differently (family involvement, indirect communication)
- Always end on hopeful, constructive note

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'but, however, not, disagree, upset, angry, frustrated, annoyed, sorry, apologize, my fault, misunderstand, clarify, explain, tension, argument, fight, issue, problem, bothering, hurt, disappointed, whatever, fine, silent, space, time, stress, difficult, hard day, tough, struggle',
  '{
  "type": "object",
  "required": [
    "conflict_presence",
    "conflict_triggers",
    "individual_styles",
    "stress_communication",
    "repair_recovery",
    "positive_behaviors",
    "destructive_patterns",
    "stress_support",
    "recommendations",
    "overall"
  ],
  "properties": {
    "conflict_presence": {
      "type": "object",
      "required": ["visible_conflicts", "frequency", "assessment"],
      "properties": {
        "visible_conflicts": {"type": "boolean"},
        "frequency": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "conflict_triggers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["trigger_type", "description"],
        "properties": {
          "trigger_type": {"type": "string"},
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
            "required": ["name", "style", "intensity", "description"],
            "properties": {
              "name": {"type": "string"},
              "style": {"type": "string"},
              "intensity": {"type": "string"},
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
    "stress_communication": {
      "type": "object",
      "required": ["pattern_description", "initiator", "changes"],
      "properties": {
        "pattern_description": {"type": "string"},
        "initiator": {"type": "string"},
        "changes": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "repair_recovery": {
      "type": "object",
      "required": ["strategies", "initiator", "timeframe", "effectiveness"],
      "properties": {
        "strategies": {
          "type": "array",
          "items": {"type": "string"}
        },
        "initiator": {"type": "string"},
        "timeframe": {"type": "string"},
        "effectiveness": {"type": "string"},
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
    "positive_behaviors": {
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
    },
    "destructive_patterns": {
      "type": "object",
      "required": ["present", "assessment"],
      "properties": {
        "present": {"type": "boolean"},
        "assessment": {"type": "string"},
        "patterns": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["pattern_type", "description", "severity"],
            "properties": {
              "pattern_type": {"type": "string"},
              "description": {"type": "string"},
              "severity": {"type": "string"},
              "evidence": {
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
    "stress_support": {
      "type": "object",
      "required": ["analysis", "evidence"],
      "properties": {
        "analysis": {"type": "string"},
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
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "target", "suggestion", "technique", "example_phrases"],
        "properties": {
          "title": {"type": "string"},
          "target": {"type": "array", "items": {"type": "string"}},
          "suggestion": {"type": "string"},
          "technique": {"type": "string"},
          "example_phrases": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "maturity_level", "summary"],
      "properties": {
        "score": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "description": "Conflict resolution maturity score (0-10)"
        },
        "maturity_level": {"type": "string"},
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
--   'a9d8e7f6-5c4b-3a2d-1e0f-9a8b7c6d5e4f'::uuid,
--   4,
--   NOW()
-- );
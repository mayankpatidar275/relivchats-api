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
Analyze how this couple handles disagreements, tension, and stressful situations. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally throughout - NEVER use "you" or single out one person
- **Evidence Context:** Describe the SITUATION, not timestamps (Good: "During a discussion about project delays" | Bad: "Messages at 2pm")
- **Evidence Exchange:** Include 2-4 actual messages per evidence item for readability
- **Focus:** Emphasize patterns and growth opportunities, not problems

Provide insights on:

1. **Conflict Presence & Frequency**:
   - Are there visible conflicts/disagreements in the chat?
   - If yes: Approximate frequency (rare, occasional, frequent)
   - If no: Is this genuinely harmonious OR are conflicts avoided/taken offline?
   - Look for: arguments, tension, "but", "however", defensive language, hurt feelings

2. **Conflict Triggers**:
   - What topics/situations spark tension?
   - Common triggers: miscommunication, unmet expectations, time/attention, external stress, family/friends
   - Provide 1-2 evidence items for each identified trigger
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
   - Provide 1-2 evidence items showing this style in action

4. **Communication Patterns Under Stress**:
   - How does communication change when stressed/upset during conflicts?
   - Look for: message frequency changes, tone shifts, emoji usage drops, shorter messages, delayed responses
   - Do they communicate stress directly ("I''m stressed") or indirectly (behavior changes)?
   - Who initiates difficult conversations?

5. **Repair & Recovery**:
   - After tension, how do they reconnect?
   - Repair strategies: direct apology, humor, gifts/gestures, time/space then return, pretend nothing happened
   - Who initiates repair more often?
   - Timeframe: immediate, hours, days
   - Provide 2-3 evidence items showing the repair process

6. **Positive Conflict Behaviors**:
   - What do they do WELL during disagreements?
   - Examples: staying respectful, validating feelings, taking breaks, using "I feel" statements, humor to diffuse
   - Identify 2-3 positive behaviors with evidence items
   - Celebrate healthy patterns

7. **Destructive Patterns** (if any):
   - Red flags: name-calling, bringing up past, "you always/never", silent treatment >24hrs, threats
   - If none: celebrate this explicitly
   - Provide evidence items if patterns exist

8. **Stress Support**:
   - When one person is stressed by external factors (work, family, health), how does partner respond?
   - Supportive responses vs adding pressure
   - Provide 2-3 evidence items showing support in action

9. **Growth Recommendations**:
   - Provide 2-3 specific, actionable suggestions based on observed patterns
   - Target recommendations to specific people when relevant (use their names in "target" field)
   - Provide 3-5 practical example phrases they can use

**INTERPRETATION GUIDELINES:**
- Be extremely careful with interpretation - not every "but" is conflict
- Never catastrophize or pathologize normal couple disagreements
- If conflicts are healthy/minor, celebrate this (most couples fight!)
- Some couples genuinely don''t fight in text - acknowledge this
- Cultural context: Indian couples may handle conflict differently (family involvement, indirect communication)
- Always end on a hopeful, constructive note

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
        "visible_conflicts": { "type": "boolean" },
        "frequency": {
          "type": "string"
        },
        "assessment": { "type": "string", "maxLength": 800 }
      }
    },
    "conflict_triggers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["trigger_type", "description", "evidence"],
        "properties": {
          "trigger_type": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["context", "exchange"],
              "properties": {
                "context": { "type": "string" },
                "exchange": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": { "type": "string" },
                      "message": { "type": "string" },
                      "timestamp": { "type": "string" }
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
            "required": [
              "name",
              "style",
              "intensity",
              "description",
              "evidence"
            ],
            "properties": {
              "name": { "type": "string" },
              "style": { "type": "string" },
              "intensity": { "type": "string" },
              "description": { "type": "string" },
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["context", "exchange"],
                  "properties": {
                    "context": { "type": "string" },
                    "exchange": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["speaker", "message", "timestamp"],
                        "properties": {
                          "speaker": { "type": "string" },
                          "message": { "type": "string" },
                          "timestamp": { "type": "string" }
                        }
                      }
                    }
                  }
                }
              }
            }
          },
          "maxItems": 2,
          "minItems": 2
        }
      }
    },
    "stress_communication": {
      "type": "object",
      "required": ["pattern_description", "initiator", "changes"],
      "properties": {
        "pattern_description": { "type": "string" },
        "initiator": { "type": "string" },
        "changes": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "repair_recovery": {
      "type": "object",
      "required": ["strategies", "initiator", "timeframe", "effectiveness", "evidence"],
      "properties": {
        "strategies": {
          "type": "array",
          "items": { "type": "string" }
        },
        "initiator": { "type": "string" },
        "timeframe": { "type": "string" },
        "effectiveness": { "type": "string" },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["context", "exchange"],
            "properties": {
              "context": { "type": "string" },
              "exchange": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["speaker", "message", "timestamp"],
                  "properties": {
                    "speaker": { "type": "string" },
                    "message": { "type": "string" },
                    "timestamp": { "type": "string" }
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
        "required": ["behavior", "description", "evidence"],
        "properties": {
          "behavior": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["context", "exchange"],
              "properties": {
                "context": { "type": "string" },
                "exchange": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": { "type": "string" },
                      "message": { "type": "string" },
                      "timestamp": { "type": "string" }
                    }
                  }
                }
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
        "present": { "type": "boolean" },
        "assessment": { "type": "string" },
        "patterns": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["pattern_type", "description", "severity", "evidence"],
            "properties": {
              "pattern_type": { "type": "string" },
              "description": { "type": "string" },
              "severity": { "type": "string" },
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["context", "exchange"],
                  "properties": {
                    "context": { "type": "string" },
                    "exchange": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["speaker", "message", "timestamp"],
                        "properties": {
                          "speaker": { "type": "string" },
                          "message": { "type": "string" },
                          "timestamp": { "type": "string" }
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
    "stress_support": {
      "type": "object",
      "required": ["analysis", "evidence"],
      "properties": {
        "analysis": { "type": "string" },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["context", "exchange"],
            "properties": {
              "context": { "type": "string" },
              "exchange": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["speaker", "message", "timestamp"],
                  "properties": {
                    "speaker": { "type": "string" },
                    "message": { "type": "string" },
                    "timestamp": { "type": "string" }
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
        "required": ["title", "target", "suggestion", "example_phrases"],
        "properties": {
          "title": { "type": "string" },
          "target": {
            "type": "array",
            "items": { "type": "string" }
          },
          "suggestion": { "type": "string" },
          "example_phrases": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "summary"],
      "properties": {
        "score": { "type": "integer", "minimum": 0, "maximum": 10 },
        "summary": { "type": "string" }
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
--   (SELECT id FROM insight_types WHERE name = 'conflict_resolution'),
--   4,
--   NOW()
-- );
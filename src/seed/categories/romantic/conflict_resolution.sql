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
- **Tone:** Write like a close friend who understands relationships - warm and conversational, NOT clinical or robotic
  * Use contractions (you''re, don''t, can''t)
  * Use short, varied sentences
  * AVOID phrases like: "demonstrates", "characterized by", "highlighting", "underlying", "the couple"
  * INSTEAD use: "often", "tends to", "usually", "sometimes", natural language
  * Example: ❌ "The couple demonstrates frequent conflicts" → ✅ "You argue often, but you don''t stay angry long"
- **Length Calibration:** Match insight depth to available content
  * Short chat (few messages, brief duration) = shorter, focused insights
  * Don''t generate filler text when there''s limited evidence
  * If there''s not enough data for a section, acknowledge it briefly rather than speculating
- **Equal Treatment:** Use BOTH participants'' names equally - NEVER single out one person or use "you"
  * Wrong: "You need to listen better" → Right: "Both could benefit from active listening"
  * Mention both names in descriptions, don''t favor one perspective
- **Evidence Context:** Describe the SITUATION clearly (what''s happening, not when)
  * Good: "When discussing work stress and sleep schedules"
  * Bad: "Messages at 2pm on Tuesday"
- **Evidence Exchange:** Include 2-4 actual messages per evidence item
- **No Repetition:** Each section should cover DISTINCT aspects - don''t repeat the same point across sections

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
   - ONLY cover what happens AFTER conflicts end - how they reconnect and make up
   - Repair strategies: direct apology, humor, gifts/gestures, time/space then return, pretend nothing happened
   - Who initiates repair more often?
   - Timeframe: immediate, hours, days
   - BOUNDARY: This is post-conflict reconnection, not behaviors during conflict (that''s Positive Behaviors)
   - Provide 2-3 evidence items showing the repair process
   - Focus on the transition from tension back to affection

6. **Positive Conflict Behaviors**:
   - What do they do WELL DURING active disagreements/conflicts?
   - Examples: staying respectful, validating feelings, taking breaks, using "I feel" statements, humor to diffuse tension
   - Identify 2-3 positive behaviors with evidence items
   - BOUNDARY: Only behaviors happening DURING conflicts, not after (that''s Repair & Recovery) or during external stress (that''s Stress Support)

7. **Destructive Patterns** (if any):
   - Red flags: name-calling, bringing up past, "you always/never", silent treatment >24hrs, threats
   - If none: celebrate this explicitly (don''t invent problems)
   - Provide evidence items if patterns exist
   - Be honest: if the chat is too short or conflicts are minor, say so

8. **Stress Support**:
   - ONLY cover support during EXTERNAL stressors (work, family, health issues, personal struggles)
   - NOT conflict-related stress - that belongs in other sections
   - How does each partner respond when the other faces external pressure?
   - BOUNDARY: This is about life stress support, not conflict support
   - Provide 2-3 evidence items showing external stress support in action
   - If no external stress visible in chat, acknowledge briefly rather than inventing scenarios

9. **Growth Recommendations**:
   - Provide 2-3 specific, actionable suggestions based on observed patterns
   - Target recommendations to specific people when relevant (use their names in "target" field)
   - Provide 3-5 practical example phrases they can use

**INTERPRETATION GUIDELINES:**
- Be extremely careful with interpretation - not every "but" is conflict
- Never catastrophize or pathologize normal couple disagreements
- If conflicts are healthy/minor, celebrate this (most couples fight!)
- Some couples genuinely don''t fight in text - acknowledge this honestly
- Cultural context: Indian couples may handle conflict differently (family involvement, indirect communication)
- Always end on a hopeful, constructive note

**CRITICAL ANTI-REPETITION RULES:**
1. Stress Support = ONLY external stressors (work, family, health) - NOT conflict support
2. Positive Behaviors = ONLY during active conflicts - NOT after conflicts end
3. Repair & Recovery = ONLY post-conflict reconnection - NOT during conflict
4. Don''t repeat the same example across multiple sections
5. If a behavior fits multiple categories, pick the MOST relevant one

**LENGTH & QUALITY RULES:**
- Short chat with few conflicts? Generate proportionally shorter insights - don''t pad with speculation
- Can''t find enough evidence? Say so honestly rather than inventing patterns
- Quality over quantity - better to have 2 solid insights than 5 weak ones
- Each description should add NEW information, not restate what was already said

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

-- -- Link to romantic category
-- INSERT INTO public.category_insight_types
-- (id, category_id, insight_type_id, display_order, created_at)
-- VALUES(
--   gen_random_uuid(),
--   (SELECT id FROM analysis_categories WHERE name = 'romantic'),
--   (SELECT id FROM insight_types WHERE name = 'conflict_resolution'),
--   4,
--   NOW()
-- );
INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  '8a3f2e1d-9c4b-4f8e-a7d6-5e8f9a2b1c3d'::uuid,
  'emotional_intimacy',
  'Emotional Intimacy',
  'Discover how you share feelings, provide support, and create emotional closeness through your conversations.',
  '💕',
  'You are analyzing emotional intimacy patterns in a romantic relationship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze emotional connection and vulnerability in this relationship. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and relationship-affirming, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally - treat partners fairly with no bias
- **Evidence Format:** Provide exact message quotes with timestamps in format [DD/MM/YY, HH:MM:SS AM/PM]
- **Evidence Quality:** Show meaningful emotional exchanges between both people, not isolated messages
- **Focus:** Emphasize beautiful connection patterns and growth opportunities, not deficits

Provide insights on:

1. **Vulnerability Expression**:
   - For EACH person: How openly do they share feelings, fears, worries, or personal struggles?
   - Look for: "I feel...", "I''m worried about...", emotional disclosures
   - Rate vulnerability level: high (frequent deep sharing), moderate (occasional sharing), low (mostly surface-level)
   - Provide 2-3 evidence messages showing vulnerability

2. **Emotional Support Patterns**:
   - For EACH person: How do they respond when the other shares something emotional?
   - Support styles: validating ("that makes sense"), problem-solving ("here''s what you can do"), empathetic ("I understand"), dismissive
   - Who initiates emotional support conversations more?
   - Provide 2-4 evidence exchanges showing support in action

3. **Affection Expression**:
   - For EACH person: How do they express care, love, or appreciation?
   - Types: compliments, miss you messages, thank you notes, terms of endearment, emojis/hearts
   - Frequency comparison between partners
   - Provide 3-4 evidence messages showing affection

4. **Emotional Check-ins**:
   - How often do they ask about each other''s feelings/well-being beyond surface greetings?
   - Examples: "How are you really feeling?", "Is everything okay?", "You seem quiet today"
   - Who initiates emotional check-ins more?
   - Provide 2-3 evidence messages

5. **Conflict & Repair**:
   - Do conversations show any tension, disagreements, or misunderstandings?
   - If yes: How do they handle it? (avoidance, direct communication, apologizing, reassurance)
   - Look for repair attempts: apologies, explanations, efforts to reconnect
   - If no conflict visible: Note this positively
   - Provide evidence if conflict/repair exists

6. **Intimacy Strengths**:
   - Identify 2-3 beautiful patterns of emotional connection
   - Examples: celebrating each other''s wins, remembering important details, consistent reassurance, playful intimacy, spiritual connection
   - Must show INTERACTION between both people (not isolated messages)
   - Provide exact message quotes with timestamps

7. **Growth Opportunities**:
   - 2 specific, actionable suggestions to deepen emotional intimacy
   - Base on actual data patterns (e.g., if support is one-sided, suggest balanced sharing)
   - Frame positively as opportunities, not criticisms
   - Include example conversation starters

**INTERPRETATION GUIDELINES:**
- Respect cultural context - Indian relationships may express intimacy differently (family involvement, indirect expressions)
- Look for Hindi/Hinglish emotional expressions: "tension mat lo", "miss you", "pyaar", etc.
- If conversations are mostly practical/surface-level, acknowledge this gently without judgment
- Never pathologize natural communication patterns - focus on what works well
- Always end on a positive, affirming note

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'love, miss you, feelings, worried, scared, happy, sad, support, care, appreciate, thank you, sorry, understand, here for you, emotional, heart, affection, compliment, concern, checking in',
  '{
    "type": "object",
    "required": [
      "vulnerability_expression",
      "emotional_support_patterns",
      "affection_expression",
      "emotional_checkins",
      "conflict_and_repair",
      "intimacy_strengths",
      "growth_opportunities",
      "overall_intimacy_assessment"
    ],
    "properties": {
      "vulnerability_expression": {
        "type": "object",
        "required": ["participants", "balance_note"],
        "properties": {
          "participants": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["name", "vulnerability_level", "description", "evidence"],
              "properties": {
                "name": {"type": "string"},
                "vulnerability_level": {
                  "type": "string",
                  "enum": ["high", "moderate", "low"],
                  "description": "How openly they share emotions"
                },
                "description": {
                  "type": "string",
                  "description": "2-3 sentences describing their vulnerability style"
                },
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
                  },
                  "minItems": 2,
                  "maxItems": 4
                }
              }
            },
            "minItems": 2,
            "maxItems": 2
          },
          "balance_note": {
            "type": "string",
            "description": "2-3 sentences on whether vulnerability is mutual or one-sided"
          }
        }
      },
      "emotional_support_patterns": {
        "type": "object",
        "required": ["participants", "reciprocity_assessment", "evidence"],
        "properties": {
          "participants": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["name", "support_style", "description"],
              "properties": {
                "name": {"type": "string"},
                "support_style": {
                  "type": "string",
                  "description": "validating, problem-solving, empathetic, or combination"
                },
                "description": {
                  "type": "string",
                  "description": "2-3 sentences on how they provide support"
                }
              }
            },
            "minItems": 2,
            "maxItems": 2
          },
          "reciprocity_assessment": {
            "type": "string",
            "description": "3-4 sentences on whether support flows both ways"
          },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["context", "exchange"],
              "properties": {
                "context": {"type": "string", "description": "What support was needed"},
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
                  },
                  "minItems": 2,
                  "maxItems": 4,
                  "description": "Back-and-forth showing support"
                }
              }
            },
            "minItems": 2,
            "maxItems": 3
          }
        }
      },
      "affection_expression": {
        "type": "object",
        "required": ["participants", "comparison", "evidence"],
        "properties": {
          "participants": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["name", "frequency", "styles", "description"],
              "properties": {
                "name": {"type": "string"},
                "frequency": {
                  "type": "string",
                  "enum": ["very_frequent", "frequent", "moderate", "occasional", "rare"]
                },
                "styles": {
                  "type": "array",
                  "items": {"type": "string"},
                  "description": "Types of affection: compliments, miss you, thank you, terms of endearment, etc."
                },
                "description": {
                  "type": "string",
                  "description": "2-3 sentences on their affection style"
                }
              }
            },
            "minItems": 2,
            "maxItems": 2
          },
          "comparison": {
            "type": "string",
            "description": "2-3 sentences comparing affection expression between partners"
          },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["message", "speaker", "timestamp", "affection_type"],
              "properties": {
                "message": {"type": "string"},
                "speaker": {"type": "string"},
                "timestamp": {"type": "string"},
                "affection_type": {"type": "string", "description": "e.g., compliment, miss you, gratitude"}
              }
            },
            "minItems": 3,
            "maxItems": 6
          }
        }
      },
      "emotional_checkins": {
        "type": "object",
        "required": ["frequency", "initiator_balance", "description", "evidence"],
        "properties": {
          "frequency": {
            "type": "string",
            "enum": ["very_frequent", "frequent", "occasional", "rare", "absent"]
          },
          "initiator_balance": {
            "type": "string",
            "description": "Who asks about feelings more? Both equally, mostly X, mostly Y"
          },
          "description": {
            "type": "string",
            "description": "3-4 sentences on emotional check-in patterns"
          },
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
            },
            "minItems": 0,
            "maxItems": 4
          }
        }
      },
      "conflict_and_repair": {
        "type": "object",
        "required": ["conflict_present", "description"],
        "properties": {
          "conflict_present": {"type": "boolean"},
          "description": {
            "type": "string",
            "description": "If conflict exists: describe handling style. If not: note positive absence"
          },
          "repair_patterns": {
            "type": "array",
            "items": {"type": "string"},
            "description": "If conflict exists: apologies, explanations, reassurance, etc."
          },
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
            },
            "maxItems": 2
          }
        }
      },
      "intimacy_strengths": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["strength_title", "description", "evidence"],
          "properties": {
            "strength_title": {"type": "string"},
            "description": {
              "type": "string",
              "description": "2-3 sentences explaining this strength"
            },
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
              },
              "minItems": 2,
              "maxItems": 4
            }
          }
        },
        "minItems": 2,
        "maxItems": 3
      },
      "growth_opportunities": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["opportunity_title", "target_participants", "suggestion", "why_it_helps", "conversation_starter"],
          "properties": {
            "opportunity_title": {"type": "string"},
            "target_participants": {
              "type": "array",
              "items": {"type": "string"}
            },
            "suggestion": {
              "type": "string",
              "description": "Specific actionable advice"
            },
            "why_it_helps": {
              "type": "string",
              "description": "1-2 sentences on benefit"
            },
            "conversation_starter": {
              "type": "string",
              "description": "Example question or phrase to try"
            }
          }
        },
        "minItems": 2,
        "maxItems": 2
      },
      "overall_intimacy_assessment": {
        "type": "object",
        "required": ["score", "rating", "summary"],
        "properties": {
          "score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10,
            "description": "Emotional intimacy score 0-10"
          },
          "rating": {
            "type": "string",
            "enum": ["deeply_connected", "well_connected", "developing", "surface_level"]
          },
          "summary": {
            "type": "string",
            "description": "Warm 4-5 sentence summary highlighting strengths and gentle growth areas"
          }
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
--   '8a3f2e1d-9c4b-4f8e-a7d6-5e8f9a2b1c3d'::uuid,
--   2,
--   NOW()
-- );
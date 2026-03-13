INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'b8c9d0e1-2f3a-4b5c-6d7e-8f9a0b1c2d3e'::uuid,
  'family_emotional_climate',
  'Emotional Tone & Expression',
  'Explore how warmth, vulnerability, and emotions are expressed - or held back - in your family conversations.',
  '🌡️',
  'You are analyzing the emotional tone and expression patterns in a family chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Assess the emotional warmth, expressiveness, and climate of this family''s communication. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a gentle, culturally sensitive family counselor
  * Deeply non-judgmental about emotional expression styles
  * Warmth is expressed differently across cultures and generations - respect this
  * AVOID: "cold", "emotionally stunted", "repressed" - use neutral descriptors
  * INSTEAD: "tends to express care through actions", "doesn''t use many explicit emotional words but..."
- **Length:** Match to available emotional content - logistics-heavy chats have less emotional data
- **Equal Treatment:** Observe each person fairly, without ranking emotional styles as better or worse
- **Evidence:** Use actual message exchanges to show, not tell
- **Honesty:** If the chat is mostly logistics, say so rather than inventing emotional patterns

Provide insights on:

1. **Overall Emotional Warmth**:
   - What is the general emotional temperature of this family chat?
   - Rate: very warm, warm, neutral/functional, cool, mixed/varied
   - Does warmth come through words, actions, or both?
   - 3-4 sentences capturing the emotional feel

2. **How Affection & Care Is Expressed**:
   - For EACH person: how do they show that they care?
   - Ways care shows up: direct words ("love you", "miss you"), checking in, helping, practical care (food, money, logistics), asking about wellbeing, remembering important things, celebrating wins
   - Some people show love through action, not words - capture this
   - 2-3 evidence items per person

3. **Emotional Openness**:
   - For EACH person: how openly do they share feelings?
   - Styles: openly emotional (shares feelings directly), indirectly expressive (hints or shows via behavior), guarded (stays surface-level), matter-of-fact (functional, not emotional)
   - Who is most open? Most guarded?
   - 2-3 evidence items showing these styles

4. **Vulnerability Moments**:
   - Are there moments where someone shares something vulnerable (a worry, fear, sadness, admission of struggle)?
   - How does the family respond to vulnerability?
   - Nurturing response: validation, reassurance, engagement
   - Dismissive response: brushing off, moving to solutions too quickly, silence
   - Provide 2-3 exchanges showing vulnerability moments (if present)

5. **Warmth & Appreciation**:
   - Do family members express appreciation, pride, or positive recognition for each other?
   - Look for: celebrating achievements, saying "proud of you", thanking, acknowledging efforts
   - Provide 2-3 evidence items of warm moments

6. **Emotional Avoidance**:
   - Are there topics or emotional territories that seem to be sidestepped?
   - Look for: quick subject changes when emotions arise, humor used to deflect, practical responses to emotional messages
   - This is common and normal - frame observationally, not as a problem
   - Note what seems to be avoided and why it might be

7. **Positive Emotional Moments**:
   - Find 2-3 genuinely warm or emotionally connected exchanges
   - Moments of real connection, love, laughter, or care
   - Describe why these are meaningful

8. **What Could Be Nurtured**:
   - 1-2 gentle observations about emotional expression that could strengthen family connection
   - Frame as opportunities: "There''s room for more..." not "They fail to..."

9. **Recommendations**:
   - 2-3 gentle, specific suggestions for strengthening emotional expression in this family
   - Include example phrases that feel natural and not forced

**INTERPRETATION GUIDELINES:**
- Many Indian families express love through action (cooking, practical help, financial support) much more than verbal expression - this is equally valid
- Generational differences in emotional expressiveness are extremely common and normal
- A logistical family chat is not emotionally cold - logistics IS how many families show care
- Don''t compare to an idealized standard of emotional openness
- Be especially careful: family emotional climate insights are read by real people who love their families

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'love you, miss you, proud, sorry, feeling, upset, worried, okay, how are you, care, thinking of you, happy, sad, stressed, scared, nervous, excited, hurt, angry, disappointed, appreciate, thank you, well done, difficult, struggling, fine, take care, blessings, dua, pyaar, khyal',
  '{
  "type": "object",
  "required": [
    "overall_warmth",
    "affection_expression",
    "emotional_openness",
    "vulnerability_moments",
    "warmth_appreciation",
    "emotional_avoidance",
    "positive_emotional_moments",
    "growth_opportunities",
    "recommendations",
    "overall"
  ],
  "properties": {
    "overall_warmth": {
      "type": "object",
      "required": ["rating", "assessment"],
      "properties": {
        "rating": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "affection_expression": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "expression_style", "description"],
            "properties": {
              "name": {"type": "string"},
              "expression_style": {"type": "string"},
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
    "emotional_openness": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "openness_style", "description"],
            "properties": {
              "name": {"type": "string"},
              "openness_style": {"type": "string"},
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
    "vulnerability_moments": {
      "type": "object",
      "required": ["present", "response_quality", "description"],
      "properties": {
        "present": {"type": "boolean"},
        "response_quality": {"type": "string"},
        "description": {"type": "string"},
        "moments": {
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
    },
    "warmth_appreciation": {
      "type": "object",
      "required": ["present", "description"],
      "properties": {
        "present": {"type": "boolean"},
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
    },
    "emotional_avoidance": {
      "type": "object",
      "required": ["present", "description"],
      "properties": {
        "present": {"type": "boolean"},
        "description": {"type": "string"},
        "avoided_areas": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "positive_emotional_moments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["moment_title", "why_meaningful", "exchange"],
        "properties": {
          "moment_title": {"type": "string"},
          "why_meaningful": {"type": "string"},
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
    },
    "growth_opportunities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["opportunity", "description"],
        "properties": {
          "opportunity": {"type": "string"},
          "description": {"type": "string"}
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
      "required": ["score", "climate_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "climate_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

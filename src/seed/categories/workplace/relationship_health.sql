INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c'::uuid,
  'workplace_relationship_health',
  'Team Relationship Health',
  'Understand the trust, respect, and interpersonal dynamics that define your working relationship.',
  '🌱',
  'You are analyzing the interpersonal relationship health between colleagues in a workplace chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Assess the quality of the working relationship - trust, respect, psychological safety, and interpersonal dynamics. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a thoughtful organizational coach who understands that work relationships are complex
  * Professional but empathetic
  * AVOID strong negative labels: "toxic", "hostile", "manipulative" (unless clearly evident)
  * INSTEAD: "communication tends to feel one-directional", "there are signs of tension"
- **Length:** Match to available interpersonal content - heavily task-focused chats have limited relationship data
- **Equal Treatment:** Observe relationship patterns between participants, not singling one out
- **Evidence:** Ground observations in actual message exchanges
- **Scope:** Acknowledge that a text chat shows only a slice of a working relationship

Provide insights on:

1. **Overall Relationship Quality**:
   - How would you describe the quality of this working relationship?
   - Rate: excellent, good, functional, strained, concerning
   - Does it feel like a positive, neutral, or difficult working relationship?
   - 3-4 sentences capturing the overall dynamic

2. **Mutual Respect**:
   - Do both parties communicate with respect?
   - Look for: polite language, acknowledgment of each other''s work, valuing opinions, not dismissing or talking down
   - Are there any signs of disrespect (condescension, dismissiveness, ignoring)?
   - Rate: high respect, generally respectful, inconsistent, low respect
   - 2-3 evidence items

3. **Psychological Safety**:
   - Do participants feel comfortable raising concerns, admitting mistakes, or asking questions?
   - Look for: "I made a mistake on X", "I''m not sure about Y, can you help?", "I''m concerned about Z"
   - Absence of psychological safety: hiding mistakes, excessive hedging, never questioning or pushing back, over-apologizing
   - Rate: high safety, moderate safety, limited safety, low safety
   - 2-3 evidence items

4. **Power Dynamics**:
   - Is communication between equals, or is there a clear power differential?
   - Healthy power dynamics: appropriate deference to seniority while maintaining voice
   - Concerning power dynamics: one person dominating all decisions, dismissing input, creating dependency
   - Note whether hierarchy seems healthy or potentially problematic
   - Acknowledge if power relationship is unknown

5. **Positive Reinforcement**:
   - Do they recognize and appreciate each other''s contributions?
   - Look for: "great job", "thanks for handling that", "well done", acknowledgment of effort
   - Who tends to express appreciation more?
   - Rate the level: frequent, moderate, occasional, rare/absent
   - 2-3 evidence items

6. **Stress & Pressure Signals**:
   - Are there visible signs of workplace stress, pressure, or strain?
   - Look for: urgency language, expressions of overwhelm, frustration about work situations, deadline pressure
   - How does stress affect communication between them?
   - Note: this is about observable signals, not a psychological assessment

7. **Interpersonal Rapport**:
   - Beyond tasks, is there a personal connection?
   - Look for: small talk, humor, asking about life outside work, showing personal interest
   - A warm working relationship vs purely transactional?
   - Rate: warm personal rapport, friendly, professional but cordial, purely transactional

8. **Relationship Strengths**:
   - 2-3 specific things this working relationship does well interpersonally
   - Focus on genuine positives

9. **Areas to Strengthen**:
   - 1-2 patterns that could improve the working relationship quality
   - Frame as growth opportunities, not criticisms

10. **Recommendations**:
    - 2-3 specific, practical suggestions to strengthen the working relationship
    - Keep these realistic and actionable for a professional context
    - Include example phrases

**INTERPRETATION GUIDELINES:**
- Professional relationships exist on a spectrum of warmth - purely transactional is often fine
- Power differentials are inherent in workplaces - assess whether they seem healthy, not whether they exist
- Stress in communication often reflects external pressures, not relationship quality
- Short or task-heavy chats reveal little about relationship quality - be honest about data limitations
- Cultural differences in formality and directness are significant in Indian workplaces - respect this
- If the chat seems healthy overall, say so clearly - positive insights matter too

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'appreciate, thank you, great work, well done, good job, stressed, overwhelmed, respect, boundary, professional, team, culture, comfortable, difficult, politics, trust, tension, pressure, mistake, sorry, concern, feedback, uncomfortable, passive, aggressive, frustrated, dismissed, ignored, valued, recognized',
  '{
  "type": "object",
  "required": [
    "overall_quality",
    "mutual_respect",
    "psychological_safety",
    "power_dynamics",
    "positive_reinforcement",
    "stress_signals",
    "interpersonal_rapport",
    "relationship_strengths",
    "areas_to_strengthen",
    "recommendations",
    "overall"
  ],
  "properties": {
    "overall_quality": {
      "type": "object",
      "required": ["rating", "assessment"],
      "properties": {
        "rating": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "mutual_respect": {
      "type": "object",
      "required": ["rating", "analysis"],
      "properties": {
        "rating": {"type": "string"},
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
    "psychological_safety": {
      "type": "object",
      "required": ["rating", "analysis"],
      "properties": {
        "rating": {"type": "string"},
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
    "power_dynamics": {
      "type": "object",
      "required": ["assessment", "description"],
      "properties": {
        "assessment": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "positive_reinforcement": {
      "type": "object",
      "required": ["level", "primary_giver", "description"],
      "properties": {
        "level": {"type": "string"},
        "primary_giver": {"type": "string"},
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
    "stress_signals": {
      "type": "object",
      "required": ["present", "description"],
      "properties": {
        "present": {"type": "boolean"},
        "description": {"type": "string"},
        "signals": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "interpersonal_rapport": {
      "type": "object",
      "required": ["rating", "description"],
      "properties": {
        "rating": {"type": "string"},
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
    "relationship_strengths": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["strength", "description"],
        "properties": {
          "strength": {"type": "string"},
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
    "areas_to_strengthen": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["area", "description"],
        "properties": {
          "area": {"type": "string"},
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
      "required": ["score", "health_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "health_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

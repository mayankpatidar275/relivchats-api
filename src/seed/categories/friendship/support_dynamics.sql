INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b'::uuid,
  'friendship_support_dynamics',
  'Support & Reciprocity',
  'Understand how you show up for each other during tough times and whether care flows both ways.',
  '🫂',
  'You are analyzing emotional support and reciprocity patterns in a friendship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how emotional support works in this friendship - who gives it, who receives it, and whether it''s mutual. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a caring, insightful observer who genuinely wants this friendship to thrive
  * Natural and warm, not clinical
  * AVOID: "subject demonstrates", "the individual exhibits"
  * INSTEAD: "tends to", "usually", "often reaches out when"
- **Length:** Match insight depth to available evidence - don''t speculate
- **Equal Treatment:** Reference both people by name, don''t single one person out as "the problem"
- **Evidence Context:** Describe what was happening (the situation), not timestamps
- **Exchanges:** Include 2-4 real messages per evidence item
- **Distinct sections:** Each section covers a different dimension of support

Provide insights on:

1. **Support Presence**:
   - Is emotional support visible in this chat?
   - How frequently do difficult topics, struggles, or emotional conversations come up?
   - Rate: very active support dynamic, present and meaningful, occasional, minimal, absent
   - 3-4 sentences assessment

2. **How Each Person Supports**:
   - For EACH person: What is their support style?
   - Styles to identify:
     * Active listener: lets the other person talk, asks follow-up questions
     * Problem-solver: offers advice, solutions, practical help
     * Validator: acknowledges feelings first ("that sounds really hard")
     * Distractor/lightener: uses humor to lift moods, changes topic to positive things
     * Quiet presence: doesn''t say much but stays engaged
     * Advice-giver: jumps to solutions quickly without much listening
   - For each: describe style with 2-3 evidence items

3. **Reciprocity Assessment**:
   - Is support mutual, or does one person consistently give more?
   - Do both people share their struggles, or does only one person open up?
   - Rate overall balance: highly reciprocal, mostly reciprocal, somewhat one-sided, clearly one-sided
   - 3-4 sentences analysis with evidence

4. **Emotional Availability**:
   - When someone shares something difficult, does the other person respond with presence?
   - Look for: quick responses to tough messages, follow-up questions, checking back in later ("hey how did that go?")
   - Delayed or absent responses to emotional moments?
   - Provide 2-3 evidence items

5. **Checking In**:
   - Do they proactively check on each other (not just when responding to shared problems)?
   - Look for: "how are you doing?", "everything okay?", "how did [thing] go?", remembering earlier worries
   - Who checks in more?
   - Provide 2-3 evidence items

6. **Support During Hard Times**:
   - Identify 2-3 moments where one person was clearly going through something difficult
   - How did the other person respond?
   - Was support offered immediately or after a delay?
   - Was there follow-up?
   - Full exchanges showing the support dynamic

7. **What This Friendship Does Well**:
   - 2-3 specific strengths in how they support each other
   - Celebrate genuine moments of good support

8. **Growth Areas**:
   - 1-2 patterns where support could be deeper or more balanced
   - Frame constructively ("there''s room to..." not "they fail to...")

9. **Recommendations**:
   - 2-3 specific, actionable suggestions
   - Include example phrases or conversation openers they could use

**INTERPRETATION GUIDELINES:**
- Some friendships are more ''fun'' than ''emotionally deep'' - neither is wrong
- Don''t label one person as bad or good - context and life circumstances affect availability
- Cultural context: Indian friendships may express care through actions (food, help) vs verbal affirmation
- If support is limited in the chat, it may mean they have those conversations in person
- Always end on a constructive, hopeful note

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'support, help, struggling, hard time, there for, difficult, stress, listen, vent, advice, comfort, care, how are you, okay, checking in, how did it go, rough, problem, feeling, sad, upset, anxious, worried, not doing well, need someone, alone, overwhelmed, emotional, sharing',
  '{
  "type": "object",
  "required": [
    "support_presence",
    "support_styles",
    "reciprocity",
    "emotional_availability",
    "checking_in",
    "hard_times_moments",
    "friendship_strengths",
    "growth_areas",
    "recommendations",
    "overall"
  ],
  "properties": {
    "support_presence": {
      "type": "object",
      "required": ["level", "assessment"],
      "properties": {
        "level": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "support_styles": {
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
    "reciprocity": {
      "type": "object",
      "required": ["balance_rating", "analysis"],
      "properties": {
        "balance_rating": {"type": "string"},
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
    "emotional_availability": {
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
    "checking_in": {
      "type": "object",
      "required": ["present", "initiator", "description"],
      "properties": {
        "present": {"type": "boolean"},
        "initiator": {"type": "string"},
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
    "hard_times_moments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["situation", "response_quality", "exchange"],
        "properties": {
          "situation": {"type": "string"},
          "response_quality": {"type": "string"},
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
    "friendship_strengths": {
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
    "growth_areas": {
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
      "required": ["score", "bond_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "bond_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);

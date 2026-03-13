INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'd4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a'::uuid,
  'friendship_trust_loyalty',
  'Trust & Reliability',
  'See how well you trust each other, keep promises, and show up when it matters most.',
  '🤝',
  'You are analyzing trust and reliability patterns in a friendship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how trust and reliability show up in this friendship. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a thoughtful friend who cares about this friendship - warm, honest, and encouraging
  * Use contractions (you''re, they''re, don''t)
  * Use natural, conversational language
  * AVOID clinical terms like "demonstrates", "exhibits", "characterized by"
  * INSTEAD use: "tends to", "usually", "often", "sometimes"
- **Length Calibration:** Match depth to available content - don''t pad with speculation
- **Equal Treatment:** Mention both participants by name fairly - don''t favor one perspective
- **Evidence Context:** Describe what was happening, not when it happened
  * Good: "When one person was going through a rough patch"
  * Bad: "Messages from last Tuesday"
- **Evidence Exchanges:** Include 2-4 actual messages per evidence item
- **No Repetition:** Each section should cover distinct aspects

Provide insights on:

1. **Reliability Patterns**:
   - Do they follow through on plans, promises, and things they say they''ll do?
   - Look for: "I''ll call you", "I''ll be there", "I''ll help", followed by evidence they did or didn''t
   - Rate each person: highly reliable, reliable, inconsistent, unreliable
   - If reliability isn''t testable from chat alone, say so honestly
   - Provide 2-3 evidence items

2. **Showing Up in Hard Moments**:
   - When one person is struggling, does the other actually show up?
   - Look for: reaching out after someone shares a problem, checking back in after tough news, remembering things that were worrying the other person
   - Who initiates care more often?
   - Provide 2-3 evidence items showing this in action

3. **Promise-Keeping & Follow-Through**:
   - Are commitments made in this chat kept?
   - Look for: "let''s do X" conversations and whether they follow up, references to plans made earlier, "remember when you said..."
   - Any patterns of saying things but not following through?
   - Provide evidence if present

4. **Confidentiality & Discretion**:
   - Is sensitive or personal information treated with respect?
   - Look for: sharing of personal struggles, secrets, family issues, relationship problems
   - Does the other person respond with care and discretion?
   - Note if there''s no visible sensitive content (that''s also fine)
   - Provide 1-2 evidence items if present

5. **Consistency of Presence**:
   - Is the friendship consistent or does it go through long silences?
   - Who initiates contact more often?
   - Are there signs of one person doing more work to maintain the friendship?
   - Rate overall: highly consistent, consistent, somewhat inconsistent, one-sided

6. **Loyalty Signals**:
   - Do they defend each other, speak positively about each other, stand in each other''s corner?
   - Look for: defending against criticism, showing pride in each other''s achievements, having each other''s back
   - Provide 2-3 evidence items if present

7. **Trust Gaps** (if any):
   - Are there signs of distrust, broken trust, or awkwardness around sensitive topics?
   - Look for: defensiveness, changing subject when certain topics come up, "don''t tell anyone", expressions of hurt from past let-downs
   - If none: celebrate this honestly

8. **Recommendations**:
   - 2-3 specific, actionable suggestions based on observed patterns
   - Target to specific people when relevant (use their names)
   - Include example phrases or actions they could try

**INTERPRETATION GUIDELINES:**
- Not every missed message is unreliability - context matters
- Friendships between busy people naturally have gaps
- Cultural context: Indian friendships may have different norms around expressing loyalty directly vs showing it through actions
- Be honest but constructive - the goal is to strengthen the friendship
- If there''s limited evidence for a section, acknowledge it briefly rather than speculating

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'trust, rely, depend, promise, said you would, showed up, there for me, kept, forgot, let down, honest, loyal, secret, tell anyone, count on, follow through, reached out, checked in, remember, you said, plan, cancelled, available, consistent, one-sided, always there, never there',
  '{
  "type": "object",
  "required": [
    "reliability_patterns",
    "showing_up",
    "promise_keeping",
    "confidentiality",
    "consistency",
    "loyalty_signals",
    "trust_gaps",
    "recommendations",
    "overall"
  ],
  "properties": {
    "reliability_patterns": {
      "type": "object",
      "required": ["participants", "assessment"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "reliability_rating", "description"],
            "properties": {
              "name": {"type": "string"},
              "reliability_rating": {"type": "string"},
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
        "assessment": {"type": "string"}
      }
    },
    "showing_up": {
      "type": "object",
      "required": ["analysis", "initiator", "evidence"],
      "properties": {
        "analysis": {"type": "string"},
        "initiator": {"type": "string"},
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
    "promise_keeping": {
      "type": "object",
      "required": ["assessment", "patterns_observed"],
      "properties": {
        "assessment": {"type": "string"},
        "patterns_observed": {
          "type": "array",
          "items": {"type": "string"}
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
    "confidentiality": {
      "type": "object",
      "required": ["assessment", "sensitive_content_present"],
      "properties": {
        "assessment": {"type": "string"},
        "sensitive_content_present": {"type": "boolean"},
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
    "consistency": {
      "type": "object",
      "required": ["rating", "initiator_balance", "description"],
      "properties": {
        "rating": {"type": "string"},
        "initiator_balance": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "loyalty_signals": {
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
    "trust_gaps": {
      "type": "object",
      "required": ["present", "assessment"],
      "properties": {
        "present": {"type": "boolean"},
        "assessment": {"type": "string"},
        "gaps": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["gap_type", "description"],
            "properties": {
              "gap_type": {"type": "string"},
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
      "required": ["score", "trust_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "trust_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);

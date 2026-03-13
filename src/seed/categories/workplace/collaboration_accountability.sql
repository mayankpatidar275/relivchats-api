INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b'::uuid,
  'workplace_collaboration',
  'Collaboration & Accountability',
  'See how well you coordinate on tasks, own responsibilities, and follow through on commitments.',
  '🎯',
  'You are analyzing collaboration quality and accountability patterns in a workplace chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how well this team/pair collaborates - task ownership, follow-through, decision-making, and handling of blockers. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a sharp, constructive project management coach
  * Practical and specific - avoid vague generalities
  * AVOID: "this person doesn''t do their job", "irresponsible"
  * INSTEAD: "task updates tend to come only when prompted", "ownership of X seems unclear"
- **Length:** Match to the volume of task-related content in the chat
- **Equal Treatment:** Observe each person''s collaboration patterns fairly
- **Evidence:** Use actual task-related exchanges as examples
- **Scope:** Focus on what''s visible in text - don''t assume about what happens outside the chat

Provide insights on:

1. **Task Ownership**:
   - How clearly do people take ownership of tasks and responsibilities?
   - For EACH person: Do they claim tasks explicitly, or is ownership ambiguous?
   - Look for: "I''ll handle X", "I''m working on Y", "that''s on me", vs vague responses or silence on ownership
   - 2-3 evidence items per person showing their ownership style

2. **Follow-Through**:
   - When tasks or commitments are made in this chat, are they completed?
   - Look for: follow-up messages confirming completion, updates volunteered, tasks that seem to disappear
   - Who follows through more reliably?
   - Rate overall: excellent, good, inconsistent, poor
   - Provide 2-3 evidence items

3. **Decision-Making**:
   - How are decisions made in this collaboration?
   - Decision styles: quick and unilateral, consultative (asks for input), slow/avoidant, consensus-seeking
   - Who tends to make the final call?
   - Are decisions communicated clearly to relevant parties?
   - 2-3 evidence items

4. **Blocker Communication**:
   - When stuck or blocked on something, do they communicate this promptly?
   - Look for: "I''m blocked on X", "waiting for Y", "can''t proceed until...", vs silent delays
   - Do they ask for help effectively when needed?
   - Rate: proactively communicates blockers, communicates when asked, rarely communicates blockers

5. **Workload Balance**:
   - Does the collaboration feel balanced in terms of effort and contribution?
   - Who initiates work, raises issues, follows up?
   - Are there signs of one person carrying more of the load?
   - Rate: well-balanced, mostly balanced, somewhat imbalanced, clearly imbalanced

6. **Meeting & Coordination Quality**:
   - How well do they coordinate logistics, meetings, and shared schedules?
   - Look for: clear scheduling, confirming attendance, sharing agendas, following up on meeting outcomes
   - Provide 2-3 evidence items if coordination is visible

7. **Collaboration Strengths**:
   - 2-3 specific things this collaboration does well
   - These are genuine strengths that are working

8. **Accountability Gaps**:
   - 2-3 specific patterns that reduce collaboration effectiveness
   - Frame constructively: "clearer ownership of X would help" not "they''re irresponsible"

9. **Recommendations**:
   - 2-3 specific, practical suggestions to strengthen collaboration
   - Include example message templates they could use

**INTERPRETATION GUIDELINES:**
- Task collaboration over text is inherently incomplete - many handoffs happen verbally or in other tools
- Async communication patterns differ from real-time - response delays may be acceptable
- Different roles have different collaboration styles - context matters
- If the chat is mostly social with little task content, acknowledge this limitation
- Don''t assume about workload or accountability outside the chat

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'done, completed, pending, blocked, need, help, deadline, assigned, task, action, responsible, follow up, status, progress, delay, waiting, update, working on, will handle, on it, I''ll take, who is, check, review, approve, by when, timeline, milestone, deliverable, output, result, share, send',
  '{
  "type": "object",
  "required": [
    "task_ownership",
    "follow_through",
    "decision_making",
    "blocker_communication",
    "workload_balance",
    "coordination_quality",
    "collaboration_strengths",
    "accountability_gaps",
    "recommendations",
    "overall"
  ],
  "properties": {
    "task_ownership": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "ownership_style", "description"],
            "properties": {
              "name": {"type": "string"},
              "ownership_style": {"type": "string"},
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
    "follow_through": {
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
    "decision_making": {
      "type": "object",
      "required": ["style", "primary_decision_maker", "analysis"],
      "properties": {
        "style": {"type": "string"},
        "primary_decision_maker": {"type": "string"},
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
    "blocker_communication": {
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
    "workload_balance": {
      "type": "object",
      "required": ["rating", "analysis", "primary_driver"],
      "properties": {
        "rating": {"type": "string"},
        "analysis": {"type": "string"},
        "primary_driver": {"type": "string"}
      }
    },
    "coordination_quality": {
      "type": "object",
      "required": ["assessment", "description"],
      "properties": {
        "assessment": {"type": "string"},
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
    "collaboration_strengths": {
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
    "accountability_gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["gap", "description", "suggestion"],
        "properties": {
          "gap": {"type": "string"},
          "description": {"type": "string"},
          "suggestion": {"type": "string"}
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
      "required": ["score", "collaboration_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "collaboration_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

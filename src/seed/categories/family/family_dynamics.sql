INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'a7b8c9d0-1e2f-3a4b-5c6d-7e8f9a0b1c2d'::uuid,
  'family_dynamics',
  'Roles & Power Dynamics',
  'Understand the unspoken roles, decision patterns, and power dynamics shaping your family communication.',
  '🏡',
  'You are analyzing roles, power dynamics, and decision-making patterns in a family chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze the family roles, hierarchy, decision-making patterns, and power dynamics visible in this chat. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a thoughtful family therapist who is warm, non-judgmental, and deeply respectful of family complexity
  * Avoid language that pathologizes normal family dynamics
  * Use natural, accessible language - not clinical terms
  * Acknowledge that family roles aren''t good or bad - just patterns
- **Length:** Match to content - don''t over-analyze limited conversations
- **Equal Treatment:** Don''t frame one person as "the problem" - roles are relational, not individual
- **Evidence:** Quote actual messages to back up observations
- **Sensitivity:** Family dynamics are sensitive - be respectful and constructive

Provide insights on:

1. **Visible Roles**:
   - What roles does each person seem to play in this family?
   - Common family roles: caretaker, decision-maker, peacekeeper, worrier, advisor, protector, mediator, problem-solver, the one who''s always asked for help, the one who holds things together
   - For EACH person: their apparent role with description
   - Provide 2-3 evidence items per person
   - Note: people can hold multiple roles

2. **Decision-Making Patterns**:
   - Who tends to make decisions or direct things in the conversation?
   - How are decisions communicated - as commands, suggestions, collaborative discussion?
   - Do others defer, push back, or engage equally?
   - Provide 2-3 evidence items showing decision dynamics

3. **Communication Hierarchy**:
   - Is communication between participants relatively equal, or is there a clear hierarchy?
   - Who tends to give information vs ask for it?
   - Who gives advice vs who receives advice?
   - Rate: highly hierarchical, somewhat hierarchical, mostly equal, equal

4. **Expectation & Obligation Patterns**:
   - Are there visible expectations placed on family members?
   - Look for: what people are expected to do, obligations mentioned, "you should", "you need to", "beta/beti", expectations around roles (earning, studying, taking care of parents, etc.)
   - Provide 2-3 evidence items if present

5. **Autonomy & Space**:
   - Do family members respect each other''s independence and personal space?
   - Look for: making decisions for others, pressure around choices, respect for different opinions, allowing disagreement
   - Is there space for individual perspectives?
   - Rate: high autonomy respected, moderate, low (over-involvement), unclear

6. **What Works Well**:
   - 2-3 specific things this family does well in how they communicate and relate
   - Focus on genuine positives - genuine care, organized coordination, someone stepping up, mutual support

7. **Patterns Worth Reflecting On**:
   - 1-2 patterns in the dynamics that, while normal in families, might be worth exploring
   - Frame carefully: "This is worth being aware of..." not "This is a problem"
   - Avoid catastrophizing

8. **Recommendations**:
   - 2-3 specific, gentle suggestions based on what was observed
   - Frame around strengthening connection and communication, not fixing people
   - Include example phrases

**INTERPRETATION GUIDELINES:**
- Family hierarchies are normal and culturally relative - don''t impose Western norms
- Indian family dynamics often include more interdependence, parental authority, and obligation - respect this
- Logistical family chats (planning, coordination) reveal less about dynamics than emotional ones
- Be extremely careful not to pathologize normal cultural practices
- If the chat is mostly logistics, be honest about limited emotional data
- Always focus on strengthening connection, not diagnosing problems

**CRITICAL NOTE:** Family dynamics are deeply personal. Write with extra care and respect. Nothing here should feel like an accusation.

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'should, need to, must, always, never, tell me, decide, family, responsibility, expect, pressure, ask, help, take care, depend, rely, advice, listen, do this, you have to, beta, beti, bhai, papa, mama, permission, approve, agree, discuss, manage, handle, who decides, my choice',
  '{
  "type": "object",
  "required": [
    "visible_roles",
    "decision_making",
    "communication_hierarchy",
    "expectation_patterns",
    "autonomy_space",
    "family_strengths",
    "patterns_to_reflect",
    "recommendations",
    "overall"
  ],
  "properties": {
    "visible_roles": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "roles", "description"],
            "properties": {
              "name": {"type": "string"},
              "roles": {
                "type": "array",
                "items": {"type": "string"}
              },
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
    "decision_making": {
      "type": "object",
      "required": ["primary_decision_maker", "style", "analysis"],
      "properties": {
        "primary_decision_maker": {"type": "string"},
        "style": {"type": "string"},
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
    "communication_hierarchy": {
      "type": "object",
      "required": ["rating", "analysis"],
      "properties": {
        "rating": {"type": "string"},
        "analysis": {"type": "string"}
      }
    },
    "expectation_patterns": {
      "type": "object",
      "required": ["present", "description"],
      "properties": {
        "present": {"type": "boolean"},
        "description": {"type": "string"},
        "expectations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["expectation_type", "directed_at", "description"],
            "properties": {
              "expectation_type": {"type": "string"},
              "directed_at": {"type": "string"},
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
    "autonomy_space": {
      "type": "object",
      "required": ["rating", "analysis"],
      "properties": {
        "rating": {"type": "string"},
        "analysis": {"type": "string"}
      }
    },
    "family_strengths": {
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
    "patterns_to_reflect": {
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
      "required": ["score", "dynamics_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "dynamics_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

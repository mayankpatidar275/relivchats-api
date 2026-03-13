INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'd0e1f2a3-4b5c-6d7e-8f9a-0b1c2d3e4f5a'::uuid,
  'workplace_communication',
  'Communication Effectiveness',
  'Assess the clarity, tone, and professional quality of communication in your work relationship.',
  '💼',
  'You are analyzing communication effectiveness and professional tone in a workplace chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how effectively these colleagues communicate - clarity, tone, responsiveness, and information flow. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like a sharp, constructive communication coach - professional but approachable
  * Focus on observable patterns, not character judgments
  * AVOID: "this person is unprofessional", "they are a bad communicator"
  * INSTEAD: "messages tend to be ambiguous", "could benefit from more explicit next steps"
- **Length:** Match to content; workplace chats vary from quick check-ins to detailed project discussions
- **Equal Treatment:** Observe each person''s communication style fairly
- **Evidence:** Use actual message examples to illustrate patterns
- **Context:** Acknowledge that informal team chats have different standards than formal emails

Provide insights on:

1. **Overall Communication Quality**:
   - How effectively does communication flow in this chat?
   - Rate: highly effective, effective, functional, inconsistent, needs improvement
   - Is it appropriately professional for the work context?
   - 3-4 sentences capturing the overall quality

2. **Clarity & Directness**:
   - For EACH person: How clear and unambiguous are their messages?
   - Look for: complete sentences vs fragments, clear requests vs vague asks, explicit next steps vs unclear outcomes, assumptions made vs explained
   - Clarity rating per person: very clear, clear, sometimes unclear, often unclear
   - 2-3 evidence items per person

3. **Tone & Professionalism**:
   - What is the overall tone? Options: formal, semi-formal, casual, overly casual, inappropriately informal
   - Is the tone consistent with the professional relationship?
   - Are there moments where tone seems off (too blunt, passive-aggressive, overly deferential)?
   - For EACH person: their typical tone with evidence

4. **Responsiveness & Acknowledgment**:
   - Do they acknowledge each other''s messages and respond to questions/requests?
   - Look for: messages left unanswered, questions that get responses, acknowledgment of completed tasks, "noted", "will do", "on it"
   - Rate: highly responsive, responsive, somewhat responsive, unresponsive
   - Note if unresponsiveness seems intentional or just communication style

5. **Information Flow**:
   - Is important information shared proactively, or only when asked?
   - Look for: updates volunteered vs waited on, relevant context provided, keeping each other in the loop
   - Who is more proactive about sharing information?
   - Rate: proactive, mostly proactive, reactive, mostly reactive

6. **Conciseness**:
   - Are messages appropriately concise, or are they overlong/underlong?
   - Look for: walls of text for simple requests, too brief for complex topics, appropriate matching of message length to complexity
   - Conciseness is context-dependent - acknowledge this

7. **Communication Strengths**:
   - 2-3 specific things this working relationship does well communicatively
   - These are genuine strengths worth preserving

8. **Communication Gaps**:
   - 2-3 specific patterns that reduce communication effectiveness
   - Frame as opportunities: "clearer next steps would help..." not "they fail to..."

9. **Recommendations**:
   - 2-3 specific, practical suggestions to improve communication effectiveness
   - Include example message templates or phrases they could use

**INTERPRETATION GUIDELINES:**
- Chat informality varies wildly by team culture - don''t impose one standard
- Fast-moving work chats prioritize speed over polish - this is often correct
- Cultural communication styles differ (direct vs indirect) - observe, don''t judge
- Asynchronous work communication has different norms than real-time chat
- If the chat is mostly logistics/coordination, note that and assess within that context
- Missing context (company culture, relationship seniority) limits interpretation - be honest about this

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'please, kindly, regarding, follow up, update, clarify, confirm, discuss, deadline, meeting, share, let me know, asap, urgent, important, action, noted, will do, on it, understood, checking, status, can you, could you, need to, should, must, unclear, confused, what do you mean, need clarification',
  '{
  "type": "object",
  "required": [
    "overall_quality",
    "clarity_directness",
    "tone_professionalism",
    "responsiveness",
    "information_flow",
    "conciseness",
    "communication_strengths",
    "communication_gaps",
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
    "clarity_directness": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "clarity_rating", "description"],
            "properties": {
              "name": {"type": "string"},
              "clarity_rating": {"type": "string"},
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
    "tone_professionalism": {
      "type": "object",
      "required": ["overall_tone", "participants", "assessment"],
      "properties": {
        "overall_tone": {"type": "string"},
        "assessment": {"type": "string"},
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "tone_description"],
            "properties": {
              "name": {"type": "string"},
              "tone_description": {"type": "string"},
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
    "responsiveness": {
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
    "information_flow": {
      "type": "object",
      "required": ["style", "proactive_participant", "analysis"],
      "properties": {
        "style": {"type": "string"},
        "proactive_participant": {"type": "string"},
        "analysis": {"type": "string"}
      }
    },
    "conciseness": {
      "type": "object",
      "required": ["assessment", "description"],
      "properties": {
        "assessment": {"type": "string"},
        "description": {"type": "string"}
      }
    },
    "communication_strengths": {
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
    "communication_gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["gap", "description", "impact"],
        "properties": {
          "gap": {"type": "string"},
          "description": {"type": "string"},
          "impact": {"type": "string"}
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
      "required": ["score", "effectiveness_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "effectiveness_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  true,
  NULL
);

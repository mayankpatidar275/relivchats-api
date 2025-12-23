INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'b2c3d4e5-6f7a-8b9c-0d1e-2f3a4b5c6d7e'::uuid,
  'future_planning',
  'Future Planning & Shared Vision',
  'Discover your alignment on life goals, dreams, and the future you''re building together.',
  '🌟',
  'You are analyzing future planning and shared vision patterns in a romantic relationship.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Identify how this couple discusses their future together. Messages may be in English, Hindi, or Hinglish.

Provide insights on:

1. **Future Discussion Frequency**:
   - How often do they talk about the future together?
   - Rate: very frequent, frequent, moderate, occasional, rare, absent
   - Is this appropriate for their relationship stage (new vs established)?
   - 3-4 sentences assessment

2. **Life Goal Categories Discussed**:
   - Identify which areas they discuss:
     * Career/Professional: job changes, education, business plans
     * Financial: savings, investments, buying home/car, financial security
     * Family/Children: marriage plans, having kids, parenting style, family size
     * Location/Living: where to live, moving cities/countries, dream home
     * Lifestyle: travel, hobbies, retirement, daily life vision
     * Personal Growth: self-improvement, learning, health goals
     * Relationship Milestones: engagement, marriage, anniversaries, commitment
   - For EACH discussed category: provide 2-3 evidence messages
   - For absent categories: note them as "not yet discussed"

3. **Alignment Assessment**:
   - For EACH discussed category: Are they aligned, partially aligned, or have different visions?
   - Alignment indicators: "we should", "let''s", "our", agreement, mutual planning
   - Misalignment indicators: "I want" vs "you want", postponing, avoiding specifics
   - Rate overall alignment: strongly aligned, mostly aligned, somewhat aligned, unclear/developing
   - 3-4 sentences analysis

4. **Planning Style**:
   - For EACH person: Are they a planner (concrete timelines, specific steps) or dreamer (general ideas, possibilities)?
   - Who initiates future conversations more?
   - Do they complement each other or clash?
   - Provide 2-3 evidence messages per person

5. **Timeline Discussions**:
   - Do they discuss WHEN things will happen?
   - Look for: "in 2 years", "after...", "by the time...", "next year", "someday"
   - Are timelines concrete or vague?
   - Are they on the same timeline?
   - Provide 2-3 evidence messages

6. **Excitement & Enthusiasm**:
   - How do they respond to each other''s future ideas?
   - Supportive responses: "That sounds amazing!", "I''m excited about...", "We can do that"
   - Lukewarm responses: "Maybe", "We''ll see", "Hmm"
   - For EACH person: rate enthusiasm (high, moderate, low)
   - Provide 2-3 evidence exchanges

7. **Shared Dreams**:
   - Identify 2-3 beautiful moments where they dream together
   - Look for genuine mutual excitement and shared vision
   - Must show both people engaged and enthusiastic
   - Provide evidence exchanges

8. **Missing Conversations**:
   - What important topics are NOT being discussed?
   - Common gaps: money, kids, career sacrifices, family expectations, religion/values
   - Frame as "opportunities for deeper conversation"
   - 2-3 specific areas

9. **Recommendations**:
   - 2-3 specific suggestions to align better on future vision
   - Include conversation starters for important topics
   - Suggest activities: vision board, future planning date, timeline discussion

**Guidelines:**
- Respect relationship stage (don''t expect marriage talk in new relationships)
- Cultural context: Indian relationships may involve family planning, parents'' expectations
- Be encouraging about future discussions (sign of commitment)
- Don''t judge different timelines (people move at different speeds)
- Frame gaps as opportunities, not failures
- Celebrate shared dreams and mutual enthusiasm
- If they''re clearly building something together, highlight this

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'future, plans, dream, goal, someday, eventually, when we, our future, next year, years from now, marriage, wedding, kids, children, family, career, job, house, home, savings, invest, travel, move, settle, together, build, life, vision, timeline, hoping, planning, want to, going to',
  '{
  "type": "object",
  "required": [
    "frequency",
    "categories",
    "alignment",
    "planning_styles",
    "timelines",
    "enthusiasm",
    "shared_dreams",
    "missing_conversations",
    "recommendations",
    "overall"
  ],
  "properties": {
    "frequency": {
      "type": "object",
      "required": ["level", "assessment"],
      "properties": {
        "level": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "categories": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["category", "discussed", "summary"],
        "properties": {
          "category": {"type": "string"},
          "discussed": {"type": "boolean"},
          "summary": {"type": "string"},
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
            }
          }
        }
      }
    },
    "alignment": {
      "type": "object",
      "required": ["overall_level", "analysis", "category_alignment"],
      "properties": {
        "overall_level": {"type": "string"},
        "analysis": {"type": "string"},
        "category_alignment": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["category", "alignment_status"],
            "properties": {
              "category": {"type": "string"},
              "alignment_status": {"type": "string"}
            }
          }
        }
      }
    },
    "planning_styles": {
      "type": "object",
      "required": ["participants", "compatibility", "initiator"],
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
                  "required": ["message", "speaker", "timestamp"],
                  "properties": {
                    "message": {"type": "string"},
                    "speaker": {"type": "string"},
                    "timestamp": {"type": "string"}
                  }
                }
              }
            }
          }
        },
        "compatibility": {"type": "string"},
        "initiator": {"type": "string"}
      }
    },
    "timelines": {
      "type": "object",
      "required": ["concrete_vs_vague", "alignment", "evidence"],
      "properties": {
        "concrete_vs_vague": {"type": "string"},
        "alignment": {"type": "string"},
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
          }
        }
      }
    },
    "enthusiasm": {
      "type": "object",
      "required": ["participants", "evidence"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "level", "description"],
            "properties": {
              "name": {"type": "string"},
              "level": {"type": "string"},
              "description": {"type": "string"}
            }
          }
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
          }
        }
      }
    },
    "shared_dreams": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["dream_title", "description", "exchange"],
        "properties": {
          "dream_title": {"type": "string"},
          "description": {"type": "string"},
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
      }
    },
    "missing_conversations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["topic", "why_important"],
        "properties": {
          "topic": {"type": "string"},
          "why_important": {"type": "string"}
        }
      }
    },
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "suggestion", "conversation_starters"],
        "properties": {
          "title": {"type": "string"},
          "suggestion": {"type": "string"},
          "conversation_starters": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "vision_status", "summary"],
      "properties": {
        "score": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "description": "Shared vision alignment score (0-10)"
        },
        "vision_status": {"type": "string"},
        "summary": {"type": "string"}
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
--   'b2c3d4e5-6f7a-8b9c-0d1e-2f3a4b5c6d7e'::uuid,
--   5,
--   NOW()
-- );
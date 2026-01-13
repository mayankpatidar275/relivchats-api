INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f'::uuid,
  'playfulness_romance',
  'Playfulness & Keeping Romance Alive',
  'See how you keep things fun, flirty, and romantic - because laughter and joy matter just as much as deep talks.',
  '😄',
  'You are analyzing playfulness, humor, and romantic spark in a relationship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Identify how this couple keeps things light, fun, and romantic. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally - treat partners fairly with no bias
- **Evidence Format:** Provide exact message quotes with timestamps in appropriate format
- **Evidence Quality:** Show meaningful interactions, not isolated messages
- **Focus:** Emphasize patterns and growth opportunities, not problems

Provide insights on:

1. **Overall Playfulness Level**:
   - How playful/fun is this chat overall?
   - Rate: highly playful, playful, balanced, serious, very serious
   - Is this appropriate for their communication context?
   - 3-4 sentences assessment

2. **Humor Styles**:
   - For EACH person: What kind of humor do they use?
   - Types: witty banter, silly/goofy, sarcastic, teasing, puns/wordplay, situational, self-deprecating, memes/references
   - Who is funnier or initiates humor more?
   - Provide 3-4 evidence messages per person showing their humor

3. **Inside Jokes & References**:
   - Do they have inside jokes, nicknames, or shared references?
   - Look for: repeated phrases, callbacks, "remember when", nicknames, emojis with special meaning
   - List 2-3 examples with context
   - This shows closeness and shared history

4. **Flirtation & Romance**:
   - How do they keep the romantic spark alive?
   - Look for: compliments, flirty emojis (😘😏💋), playful teasing, sweet messages, "miss you", romantic plans
   - For EACH person: rate flirtation frequency (very frequent, frequent, moderate, occasional, rare)
   - Provide 3-4 evidence messages

5. **Teasing & Banter**:
   - Do they playfully tease each other?
   - Healthy teasing: lighthearted, reciprocal, followed by laughs/emojis
   - Unhealthy teasing: one-sided, hurtful, without positive tone
   - Assess: balanced fun, one-sided, absent, or crosses boundaries
   - Provide 2-3 evidence exchanges

6. **Spontaneity & Surprises**:
   - Do they surprise each other with spontaneous messages, plans, or gestures?
   - Look for: random "thinking of you", surprise plans, unexpected compliments, spontaneous emojis
   - Who is more spontaneous?
   - Provide 2-3 evidence messages

7. **Emoji & GIF Usage**:
   - How do they use emojis to add playfulness?
   - Look for: playful emojis (😂🤣😜😋), romantic emojis (❤️💕😘), creative combinations
   - Do they match each other''s emoji energy?
   - Provide statistics if available, otherwise qualitative assessment

8. **Fun Activities & Plans**:
   - Do they discuss fun things to do together?
   - Look for: date ideas, travel plans, movies/shows, games, adventures, trying new things
   - Provide 2-3 evidence messages

9. **Mood Lifting**:
   - When one person seems down, does the other try to cheer them up with humor?
   - Look for: jokes when stressed, funny messages after tough days, playful distraction
   - Provide 2-3 evidence exchanges if present

10. **Romance Maintenance**:
   - How do they maintain romance in daily chats?
   - Look for: good morning/night messages with love, random "I love you", compliments, planning romantic moments
   - Rate: excellent, good, moderate, needs improvement
   - Provide evidence

11. **Playfulness Gaps**:
   - What''s missing that could add more fun?
   - Areas: more banter, inside jokes, surprise messages, date planning, flirty energy
   - 2-3 specific suggestions

12. **Best Playful Moments**:
   - Find 2-3 exchanges that capture their playful/romantic dynamic perfectly
   - Moments of genuine joy, laughter, or romantic connection
   - Provide full exchanges with context

13. **Recommendations**:
   - 2-3 specific suggestions to keep romance and fun alive
   - Include: playful challenge ideas, flirt prompts, fun conversation games
   - Provide example messages

**INTERPRETATION GUIDELINES:**
- Respect cultural humor differences (Indian couples may use different references)
- Balance is key (some couples are naturally more serious - that''s okay)
- Don''t judge emoji usage (some people just text differently)

**Output:** Return JSON matching the provided schema.',
  true,
  50,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'haha, lol, funny, joke, kidding, lmao, rofl, 😂, 🤣, 😄, 😆, cute, silly, crazy, random, fun, play, tease, flirt, 😘, 😏, 💋, ❤️, babe, baby, jaan, darling, miss you, love you, remember when, inside joke, nickname, surprise, spontaneous, date, plan, movie, adventure',
  '{
  "type": "object",
  "required": [
    "overall_playfulness",
    "humor_styles",
    "inside_jokes",
    "flirtation",
    "teasing_banter",
    "spontaneity",
    "emoji_usage",
    "fun_activities",
    "mood_lifting",
    "romance_maintenance",
    "playfulness_gaps",
    "best_moments",
    "recommendations",
    "overall"
  ],
  "properties": {
    "overall_playfulness": {
      "type": "object",
      "required": ["level", "assessment"],
      "properties": {
        "level": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "humor_styles": {
      "type": "object",
      "required": ["participants", "initiator"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "humor_types", "description"],
            "properties": {
              "name": {"type": "string"},
              "humor_types": {
                "type": "array",
                "items": {"type": "string"}
              },
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
        "initiator": {"type": "string"}
      }
    },
    "inside_jokes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["joke_or_reference", "context", "evidence"],
        "properties": {
          "joke_or_reference": {"type": "string"},
          "context": {"type": "string"},
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
    "flirtation": {
      "type": "object",
      "required": ["participants", "balance", "evidence"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "frequency", "style"],
            "properties": {
              "name": {"type": "string"},
              "frequency": {"type": "string"},
              "style": {"type": "string"}
            }
          }
        },
        "balance": {"type": "string"},
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
    "teasing_banter": {
      "type": "object",
      "required": ["present", "assessment", "balance"],
      "properties": {
        "present": {"type": "boolean"},
        "assessment": {"type": "string"},
        "balance": {"type": "string"},
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
    "spontaneity": {
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
    "emoji_usage": {
      "type": "object",
      "required": ["description", "match_level"],
      "properties": {
        "description": {"type": "string"},
        "match_level": {"type": "string"}
      }
    },
    "fun_activities": {
      "type": "object",
      "required": ["discussed", "types"],
      "properties": {
        "discussed": {"type": "boolean"},
        "types": {
          "type": "array",
          "items": {"type": "string"}
        },
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
    },
    "mood_lifting": {
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
    "romance_maintenance": {
      "type": "object",
      "required": ["rating", "description"],
      "properties": {
        "rating": {"type": "string"},
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
    },
    "playfulness_gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["gap", "suggestion"],
        "properties": {
          "gap": {"type": "string"},
          "suggestion": {"type": "string"}
        }
      }
    },
    "best_moments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["moment_title", "why_special", "exchange"],
        "properties": {
          "moment_title": {"type": "string"},
          "why_special": {"type": "string"},
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
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "suggestion", "examples"],
        "properties": {
          "title": {"type": "string"},
          "suggestion": {"type": "string"},
          "examples": {
            "type": "array",
            "items": {"type": "string"}
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "spark_status", "summary"],
      "properties": {
        "score": {
          "type": "integer",
          "minimum": 0,
          "maximum": 10,
          "description": "Playfulness and romance spark score (0-10)"
        },
        "spark_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);

-- -- Link to romantic category
INSERT INTO public.category_insight_types
(id, category_id, insight_type_id, display_order, created_at)
VALUES(
  gen_random_uuid(),
  (SELECT id FROM analysis_categories WHERE name = 'romantic'),
  (SELECT id FROM insight_types WHERE name = 'playfulness_romance'),
  5,
  NOW()
);
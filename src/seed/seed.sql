
-- Insert new packages (Final Plan)
INSERT INTO credit_packages (id, name, coins, price_usd, price_inr, description, is_active, is_popular, sort_order, stripe_price_id) 
VALUES
(
    gen_random_uuid(),
    'Starter',
    400,
    4.99,
    399,
    'Perfect for trying your first romantic analysis',
    true,
    false,
    1,
    NULL
),
(
    gen_random_uuid(),
    'Popular',
    850,
    9.99,
    799,
    'Best value - Unlock 2 romantic insights with extra coins',
    true,
    true,  -- Mark as popular
    2,
    NULL
),
(
    gen_random_uuid(),
    'Pro',
    1600,
    17.99,
    1499,
    'Power user pack - Analyze multiple chats or categories',
    true,
    false,
    3,
    NULL
);




INSERT INTO public.analysis_categories
(id, "name", display_name, description, icon, is_active, created_at, credit_cost)
VALUES(    gen_random_uuid(), -- PostgreSQL function to generate a new UUID
 'romantic', 
 'Romantic Relationship', 
 'Analysis of communication patterns and dynamics within romantic partnerships.', 
 '❤️', 
 true, 
 '2025-11-10 22:59:32.531', 
 400
);





INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'a9d8e7f6-5c4b-3a2d-1e0f-9a8b7c6d5e4f'::uuid,
  'conflict_resolution',
  'Conflict & Communication Under Stress',
  'Understand how you handle disagreements, stress, and difficult conversations - and learn to fight fair.',
  '⚖️',
  'You are analyzing conflict resolution and stress communication patterns in a romantic relationship.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Analyze how this couple handles disagreements, tension, and stressful situations. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally throughout - NEVER use "you" or single out one person
- **Evidence Context:** Describe the SITUATION, not timestamps (Good: "During a discussion about project delays" | Bad: "Messages at 2pm")
- **Evidence Exchange:** Include 2-4 actual messages per evidence item for readability
- **Focus:** Emphasize patterns and growth opportunities, not problems

Provide insights on:

1. **Conflict Presence & Frequency**:
   - Are there visible conflicts/disagreements in the chat?
   - If yes: Approximate frequency (rare, occasional, frequent)
   - If no: Is this genuinely harmonious OR are conflicts avoided/taken offline?
   - Look for: arguments, tension, "but", "however", defensive language, hurt feelings

2. **Conflict Triggers**:
   - What topics/situations spark tension?
   - Common triggers: miscommunication, unmet expectations, time/attention, external stress, family/friends
   - Provide 1-2 evidence items for each identified trigger
   - If no conflicts: state "No clear conflict triggers identified"

3. **Individual Conflict Styles**:
   - For EACH person: How do they behave during disagreements?
   - Styles to identify:
     * Avoidant: withdraws, goes silent, changes subject, "whatever", "fine"
     * Competitive: defensive, wants to win, raises counterpoints, "you always..."
     * Collaborative: seeks understanding, asks questions, "help me understand", compromises
     * Accommodating: quickly apologizes, gives in, prioritizes peace over resolution
     * Passive-aggressive: indirect criticism, sarcasm, subtle digs
   - Rate intensity: low, moderate, high
   - Provide 1-2 evidence items showing this style in action

4. **Communication Patterns Under Stress**:
   - How does communication change when stressed/upset during conflicts?
   - Look for: message frequency changes, tone shifts, emoji usage drops, shorter messages, delayed responses
   - Do they communicate stress directly ("I''m stressed") or indirectly (behavior changes)?
   - Who initiates difficult conversations?

5. **Repair & Recovery**:
   - After tension, how do they reconnect?
   - Repair strategies: direct apology, humor, gifts/gestures, time/space then return, pretend nothing happened
   - Who initiates repair more often?
   - Timeframe: immediate, hours, days
   - Provide 2-3 evidence items showing the repair process

6. **Positive Conflict Behaviors**:
   - What do they do WELL during disagreements?
   - Examples: staying respectful, validating feelings, taking breaks, using "I feel" statements, humor to diffuse
   - Identify 2-3 positive behaviors with evidence items
   - Celebrate healthy patterns

7. **Destructive Patterns** (if any):
   - Red flags: name-calling, bringing up past, "you always/never", silent treatment >24hrs, threats
   - If none: celebrate this explicitly
   - Provide evidence items if patterns exist

8. **Stress Support**:
   - When one person is stressed by external factors (work, family, health), how does partner respond?
   - Supportive responses vs adding pressure
   - Provide 2-3 evidence items showing support in action

9. **Growth Recommendations**:
   - Provide 2-3 specific, actionable suggestions based on observed patterns
   - Target recommendations to specific people when relevant (use their names in "target" field)
   - Provide 3-5 practical example phrases they can use

**INTERPRETATION GUIDELINES:**
- Be extremely careful with interpretation - not every "but" is conflict
- Never catastrophize or pathologize normal couple disagreements
- If conflicts are healthy/minor, celebrate this (most couples fight!)
- Some couples genuinely don''t fight in text - acknowledge this
- Cultural context: Indian couples may handle conflict differently (family involvement, indirect communication)
- Always end on a hopeful, constructive note

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'but, however, not, disagree, upset, angry, frustrated, annoyed, sorry, apologize, my fault, misunderstand, clarify, explain, tension, argument, fight, issue, problem, bothering, hurt, disappointed, whatever, fine, silent, space, time, stress, difficult, hard day, tough, struggle',
  '{
  "type": "object",
  "required": [
    "conflict_presence",
    "conflict_triggers",
    "individual_styles",
    "stress_communication",
    "repair_recovery",
    "positive_behaviors",
    "destructive_patterns",
    "stress_support",
    "recommendations",
    "overall"
  ],
  "properties": {
    "conflict_presence": {
      "type": "object",
      "required": ["visible_conflicts", "frequency", "assessment"],
      "properties": {
        "visible_conflicts": { "type": "boolean" },
        "frequency": {
          "type": "string"
        },
        "assessment": { "type": "string", "maxLength": 800 }
      }
    },
    "conflict_triggers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["trigger_type", "description", "evidence"],
        "properties": {
          "trigger_type": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["context", "exchange"],
              "properties": {
                "context": { "type": "string" },
                "exchange": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": { "type": "string" },
                      "message": { "type": "string" },
                      "timestamp": { "type": "string" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "individual_styles": {
      "type": "object",
      "required": ["participants"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": [
              "name",
              "style",
              "intensity",
              "description",
              "evidence"
            ],
            "properties": {
              "name": { "type": "string" },
              "style": { "type": "string" },
              "intensity": { "type": "string" },
              "description": { "type": "string" },
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["context", "exchange"],
                  "properties": {
                    "context": { "type": "string" },
                    "exchange": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["speaker", "message", "timestamp"],
                        "properties": {
                          "speaker": { "type": "string" },
                          "message": { "type": "string" },
                          "timestamp": { "type": "string" }
                        }
                      }
                    }
                  }
                }
              }
            }
          },
          "maxItems": 2,
          "minItems": 2
        }
      }
    },
    "stress_communication": {
      "type": "object",
      "required": ["pattern_description", "initiator", "changes"],
      "properties": {
        "pattern_description": { "type": "string" },
        "initiator": { "type": "string" },
        "changes": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },
    "repair_recovery": {
      "type": "object",
      "required": ["strategies", "initiator", "timeframe", "effectiveness", "evidence"],
      "properties": {
        "strategies": {
          "type": "array",
          "items": { "type": "string" }
        },
        "initiator": { "type": "string" },
        "timeframe": { "type": "string" },
        "effectiveness": { "type": "string" },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["context", "exchange"],
            "properties": {
              "context": { "type": "string" },
              "exchange": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["speaker", "message", "timestamp"],
                  "properties": {
                    "speaker": { "type": "string" },
                    "message": { "type": "string" },
                    "timestamp": { "type": "string" }
                  }
                }
              }
            }
          }
        }
      }
    },
    "positive_behaviors": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["behavior", "description", "evidence"],
        "properties": {
          "behavior": { "type": "string" },
          "description": { "type": "string" },
          "evidence": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["context", "exchange"],
              "properties": {
                "context": { "type": "string" },
                "exchange": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["speaker", "message", "timestamp"],
                    "properties": {
                      "speaker": { "type": "string" },
                      "message": { "type": "string" },
                      "timestamp": { "type": "string" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "destructive_patterns": {
      "type": "object",
      "required": ["present", "assessment"],
      "properties": {
        "present": { "type": "boolean" },
        "assessment": { "type": "string" },
        "patterns": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["pattern_type", "description", "severity", "evidence"],
            "properties": {
              "pattern_type": { "type": "string" },
              "description": { "type": "string" },
              "severity": { "type": "string" },
              "evidence": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["context", "exchange"],
                  "properties": {
                    "context": { "type": "string" },
                    "exchange": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "required": ["speaker", "message", "timestamp"],
                        "properties": {
                          "speaker": { "type": "string" },
                          "message": { "type": "string" },
                          "timestamp": { "type": "string" }
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
    "stress_support": {
      "type": "object",
      "required": ["analysis", "evidence"],
      "properties": {
        "analysis": { "type": "string" },
        "evidence": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["context", "exchange"],
            "properties": {
              "context": { "type": "string" },
              "exchange": {
                "type": "array",
                "items": {
                  "type": "object",
                  "required": ["speaker", "message", "timestamp"],
                  "properties": {
                    "speaker": { "type": "string" },
                    "message": { "type": "string" },
                    "timestamp": { "type": "string" }
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
          "title": { "type": "string" },
          "target": {
            "type": "array",
            "items": { "type": "string" }
          },
          "suggestion": { "type": "string" },
          "example_phrases": {
            "type": "array",
            "items": { "type": "string" }
          }
        }
      }
    },
    "overall": {
      "type": "object",
      "required": ["score", "summary"],
      "properties": {
        "score": { "type": "integer", "minimum": 0, "maximum": 10 },
        "summary": { "type": "string" }
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);



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

**FORMATTING GUIDELINES:**
- **Tone:** Write like a warm, insightful relationship counselor - supportive and constructive, not clinical or judgmental
- **Length:** Keep all descriptions concise (2-3 sentences maximum)
- **Equal Treatment:** Use both participants'' names equally - treat partners fairly with no bias
- **Evidence Format:** Provide exact message quotes with timestamps in appropriate format
- **Evidence Quality:** Show meaningful interactions, not isolated messages
- **Focus:** Emphasize patterns and growth opportunities, not problems

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

**INTERPRETATION GUIDELINES:**
- Respect relationship stage (don''t expect marriage talk in new relationships)
- Cultural context: Indian relationships may involve family planning, parents'' expectations
- Don''t judge different timelines (people move at different speeds)

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





INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'conflict_resolution'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'future_planning'),
    1
);

INSERT INTO category_insight_types (id, category_id, insight_type_id, display_order)
VALUES (
    gen_random_uuid(), -- FIX: Explicitly generate the UUID for the primary key
    (SELECT id FROM analysis_categories WHERE name = 'romantic'),
    (SELECT id FROM insight_types WHERE name = 'playfulness_romance'),
    1
);


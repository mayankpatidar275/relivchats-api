INSERT INTO public.insight_types
(id, "name", display_title, description, icon, prompt_template, is_premium, credit_cost, estimated_tokens, avg_generation_time_ms, is_active, created_at, updated_at, rag_query_keywords, response_schema, required_metadata_fields, supports_group_chats, max_participants)
VALUES(
  'f6a7b8c9-0d1e-2f3a-4b5c-6d7e8f9a0b1c'::uuid,
  'friendship_vitality',
  'Connection & Fun',
  'Discover how alive and energetic your friendship is - the humor, plans, inside jokes, and effort that keep it thriving.',
  '⚡',
  'You are analyzing the vitality, energy, and connection quality of a friendship chat.

**Chat Details:**
- Participants: {participant_list}
- Total Messages: {total_messages}
- Duration: {total_days} days

**Chat Statistics:**
{metadata}

**Sample Conversations ({total_chunks} excerpts):**
{chunks}

**Your Task:**
Assess how alive and energetic this friendship is - the fun, humor, shared activities, and effort that keep it going. Messages may be in English, Hindi, or Hinglish.

**FORMATTING GUIDELINES:**
- **Tone:** Like an enthusiastic, perceptive friend who appreciates what makes friendships special
  * Warm, upbeat, honest
  * AVOID robotic language: "exhibits high engagement levels"
  * INSTEAD: "they have a great banter going", "you can feel the energy in these exchanges"
- **Length:** Match to available content - short chat = concise insights
- **Equal Treatment:** Give both people fair credit for keeping the friendship alive
- **Evidence:** Show actual exchanges that capture the friendship''s energy
- **No Repetition:** Don''t repeat the same example across sections

Provide insights on:

1. **Overall Energy Level**:
   - How vibrant and alive does this friendship feel?
   - Rate: extremely energetic, lively, moderate, low-key/comfortable, quiet/distant
   - Is this level appropriate for a long friendship vs a newer one?
   - 3-4 sentences capturing the overall vibe

2. **Humor & Banter**:
   - How much do they laugh, joke, and tease each other?
   - Humor styles: silly, witty, sarcastic, meme-heavy, self-deprecating, teasing banter, situational
   - For EACH person: their humor style and how much they contribute
   - Who is funnier or initiates jokes more?
   - 3-4 evidence items showing their humor

3. **Inside Jokes & Shared References**:
   - Do they have their own language, nicknames, callbacks, running jokes?
   - Look for: repeated phrases, references to past events, nicknames, emojis with special meaning, "remember when"
   - List 2-3 examples with context - these show depth and shared history

4. **Plans & Shared Activities**:
   - Do they make plans, discuss activities, or talk about things to do together?
   - Look for: suggesting hangouts, talking about mutual interests, past activities they did together, things they want to try
   - How often are plans made vs actually followed through?
   - Provide 2-3 evidence items

5. **Initiation Balance**:
   - Who reaches out first more often?
   - Who starts conversations vs who responds?
   - Is the friendship being maintained equally, or does one person do most of the work?
   - Rate: well-balanced, mostly balanced, somewhat one-sided, clearly one-sided

6. **Depth of Conversation**:
   - Does the chat go beyond small talk and logistics?
   - Look for: real conversations about life, feelings, opinions, meaningful topics
   - Rate: deep and meaningful, good mix, mostly surface level, primarily logistics
   - Provide 2-3 evidence items of meaningful exchanges

7. **Excitement & Enthusiasm**:
   - How enthusiastically do they respond to each other?
   - Look for: long replies, exclamation points, follow-up questions showing genuine interest, engagement with what the other shares
   - Who tends to be more enthusiastic?
   - 2-3 evidence items

8. **Best Friendship Moments**:
   - Find 2-3 exchanges that best capture this friendship''s energy and connection
   - Moments of genuine joy, laughter, deep conversation, or warm connection
   - Describe why each moment is special

9. **Vitality Gaps**:
   - What''s missing that could make this friendship more vibrant?
   - Areas: more initiation from one side, deeper conversations, more shared activities, humor, showing up for each other more
   - 2-3 specific gaps, framed constructively

10. **Recommendations**:
    - 2-3 actionable suggestions to boost friendship energy
    - Include specific ideas (activities, conversation topics, challenges they could try)

**INTERPRETATION GUIDELINES:**
- Some friendships are naturally quieter - respect different friendship styles
- A low-key chat doesn''t mean a weak friendship if the support is solid
- Cultural context: Indian friendships often express closeness through sharing life updates and food/activity plans more than overtly emotional language
- Long-standing friendships may have fewer fireworks but deeper roots - acknowledge this
- Don''t confuse texting frequency with friendship quality

**Output:** Return JSON matching the provided schema.',
  true,
  100,
  NULL,
  NULL,
  true,
  NOW(),
  NULL,
  'haha, lol, funny, joke, kidding, plans, hangout, meet, miss you, remember when, should do, laugh, banter, tease, game, watch, trip, excited, catch up, what are you up to, busy, fun, crazy, omg, yaar, bhai, dude, we should, let''s, last time, that time when, inside joke, nickname',
  '{
  "type": "object",
  "required": [
    "energy_level",
    "humor_banter",
    "inside_references",
    "shared_activities",
    "initiation_balance",
    "conversation_depth",
    "enthusiasm",
    "best_moments",
    "vitality_gaps",
    "recommendations",
    "overall"
  ],
  "properties": {
    "energy_level": {
      "type": "object",
      "required": ["rating", "assessment"],
      "properties": {
        "rating": {"type": "string"},
        "assessment": {"type": "string"}
      }
    },
    "humor_banter": {
      "type": "object",
      "required": ["participants", "initiator"],
      "properties": {
        "participants": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "humor_style", "description"],
            "properties": {
              "name": {"type": "string"},
              "humor_style": {"type": "string"},
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
    "inside_references": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["reference", "context"],
        "properties": {
          "reference": {"type": "string"},
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
    "shared_activities": {
      "type": "object",
      "required": ["discussed", "activity_types", "follow_through_assessment"],
      "properties": {
        "discussed": {"type": "boolean"},
        "activity_types": {
          "type": "array",
          "items": {"type": "string"}
        },
        "follow_through_assessment": {"type": "string"},
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
    "initiation_balance": {
      "type": "object",
      "required": ["rating", "description", "primary_initiator"],
      "properties": {
        "rating": {"type": "string"},
        "description": {"type": "string"},
        "primary_initiator": {"type": "string"}
      }
    },
    "conversation_depth": {
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
    "enthusiasm": {
      "type": "object",
      "required": ["participants"],
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
    "vitality_gaps": {
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
      "required": ["score", "friendship_status", "summary"],
      "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 10},
        "friendship_status": {"type": "string"},
        "summary": {"type": "string"}
      }
    }
  }
}'::jsonb,
  '["total_messages", "total_days", "user_stats"]'::jsonb,
  false,
  2
);

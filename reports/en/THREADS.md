# Conversations: single message vs conversation-aware

Replays the 32 hand-written conversations in `data/en/threads.jsonl` (16 slow-burn scams, 16 normal chats,
committed before this feature was written) one incoming message at a time. A conversation is *warned* if any
message reaches the level.

| Mode | Level | Scam conversations warned | Avg. message of first warning | Normal conversations warned |
|---|---|---|---|---|
| single | medium | 14/16 | 2.5 | 0/16 |
| single | high | 14/16 | 2.71 | 0/16 |
| thread | medium | 16/16 | 2.62 | 0/16 |
| thread | high | 15/16 | 2.67 | 0/16 |

Safety net: 2 of 16 normal conversations get a "verify before paying / never share
codes" caution (they ask for money or codes, so that is intended), and 0 scam
conversations that are never warned still get that caution.

Still missed in conversation mode (never reach medium): none.

Caveat: 32 conversations written by the same author as the templates. Directionally useful, not a benchmark.

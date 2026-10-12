# Streaming trigger implementation

Scope approved by user: O(n) physical thresholds, time derivatives, EWMA,
merge adjacent trigger windows; stop active analysis; evaluate three local clips;
commit relevant backend/Qwen/upload files and automatic AI session log to the
existing feat/qwen_7b_local branch. Exclude tests, caches and unrelated deletions.

1. Add streaming log-clock trigger service with bounded state and flag samples.
   Validate derivatives, stationary position, compass wrap, time gaps, EWMA,
   unsynchronized logs, merging and frame index conversion using regression tests.
2. Connect candidate detection and local pipeline; persist raw log triggers even
   without synchronization. Never infer offset from row zero or nominal FPS.
   Use probed FPS when available, 24 FPS only as a default. Remove acceleration-only
   candidate pruning. Keep existing SQL/evidence/provider flow and video-only A/B.
3. Run detection on all three MP4/CSV pairs, probe real media, compare trigger
   neighborhoods with held-out expected references, inspect frames/clips where
   clock mapping is verified. Save measured artifacts and limitations.
4. Fix AI log inclusion and automatic pre-commit staging without automatically
   transmitting to a grading service. Validate JSONL and secret exposure before push.
5. Run required checks, inspect exact staged file list, commit with the requested
   message, push existing branch, verify remote SHA and tracked session log.

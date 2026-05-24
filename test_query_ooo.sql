-- 顯示 interspersed (交錯) 的 APP slice，包含 UI 執行與 RenderThread 出圖流程 (Vulkan Queue Submit & Present)
-- 並將 counters 混合在一起，驗證整體時序的正確性。
SELECT
  'slice' AS type,
  slice.ts,
  thread.name AS thread_or_track_name,
  slice.name AS detail
FROM slice
JOIN thread_track
  ON slice.track_id = thread_track.id
JOIN thread
  USING (utid)
UNION ALL
SELECT
  'counter' AS type,
  ts,
  track.name AS thread_or_track_name,
  'value: ' || value AS detail
FROM counter
JOIN track
  ON counter.track_id = track.id
WHERE
  track.name LIKE "ooo_counter_%"
ORDER BY
  ts ASC;

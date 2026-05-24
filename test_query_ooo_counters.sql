-- 驗證 out-of-order counter 事件是否被正確排序且 id 有按 ts 由小到大遞增
-- 如果 TraceSorter 運作正常，雖然我們送入的 offsets 是穿插非單調的，
-- 排序後在 database 中仍應以 ts 由小到大排列（此時對應的 counter.id 也應該是遞增的）。
SELECT
  counter.id,
  ts,
  name,
  value
FROM counter
JOIN track
  ON counter.track_id = track.id
WHERE
  name LIKE "ooo_counter_%"
ORDER BY
  counter.id ASC;

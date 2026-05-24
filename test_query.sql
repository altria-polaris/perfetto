SELECT
  ts,
  name,
  value
FROM counter
JOIN track
  ON counter.track_id = track.id
WHERE
  name LIKE "%example_counter%";

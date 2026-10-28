-- Воронка: сколько лидов дошло до каждой стадии (и доля от всех лидов).
CREATE VIEW funnel AS
WITH totals AS (
    SELECT count(*) AS all_leads FROM leads
),
reached AS (
    SELECT stage, count(DISTINCT lead_id) AS leads_count
    FROM stage_events
    GROUP BY stage
)
SELECT r.stage,
       r.leads_count,
       round(100.0 * r.leads_count / t.all_leads, 1) AS pct_of_all
FROM reached r
CROSS JOIN totals t
ORDER BY array_position(ARRAY['new', 'qualified', 'proposal', 'won', 'lost'], r.stage);

-- Время, которое лид провёл в каждой стадии (LEAD по истории переходов).
CREATE VIEW time_in_stage AS
SELECT lead_id,
       stage,
       at AS entered_at,
       lead(at) OVER (PARTITION BY lead_id ORDER BY at) AS left_at,
       lead(at) OVER (PARTITION BY lead_id ORDER BY at) - at AS spent
FROM stage_events;

-- Конверсия и среднее время до «won» по источникам.
CREATE VIEW source_conversion AS
SELECT l.source,
       count(*) AS leads_count,
       count(*) FILTER (WHERE won.lead_id IS NOT NULL) AS won_count,
       round(100.0 * count(*) FILTER (WHERE won.lead_id IS NOT NULL) / count(*), 1) AS win_rate_pct,
       coalesce(sum(l.amount) FILTER (WHERE won.lead_id IS NOT NULL), 0) AS won_amount,
       justify_interval(avg(won.at - l.created_at)) AS avg_time_to_win
FROM leads l
LEFT JOIN stage_events won ON won.lead_id = l.id AND won.stage = 'won'
GROUP BY l.source;

-- Рейтинг менеджеров: выручка, место (RANK) и доля от общей выручки.
CREATE VIEW manager_ranking AS
WITH per_manager AS (
    SELECT m.id AS manager_id,
           m.name,
           count(l.id) AS leads_count,
           count(w.lead_id) AS won_count,
           coalesce(sum(l.amount) FILTER (WHERE w.lead_id IS NOT NULL), 0) AS won_amount
    FROM managers m
    LEFT JOIN leads l ON l.manager_id = m.id
    LEFT JOIN stage_events w ON w.lead_id = l.id AND w.stage = 'won'
    GROUP BY m.id, m.name
)
SELECT manager_id,
       name,
       leads_count,
       won_count,
       won_amount,
       rank() OVER (ORDER BY won_amount DESC) AS place,
       round(100.0 * won_amount / nullif(sum(won_amount) OVER (), 0), 1) AS share_pct
FROM per_manager;

-- Новые лиды по дням со скользящим средним за 7 дней.
-- Дни без лидов добавляются через generate_series, иначе окно «7 строк» растянулось бы на больше 7 дней.
CREATE VIEW daily_leads AS
WITH bounds AS (
    SELECT min(created_at)::date AS first_day, max(created_at)::date AS last_day FROM leads
),
calendar AS (
    SELECT d::date AS day
    FROM bounds, generate_series(bounds.first_day, bounds.last_day, interval '1 day') AS d
),
per_day AS (
    SELECT c.day, count(l.id) AS leads_count
    FROM calendar c
    LEFT JOIN leads l ON l.created_at::date = c.day
    GROUP BY c.day
)
SELECT day,
       leads_count,
       round(avg(leads_count) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS avg_7d
FROM per_day
ORDER BY day;

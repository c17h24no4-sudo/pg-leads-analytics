CREATE TABLE managers (
    id    serial PRIMARY KEY,
    name  text NOT NULL UNIQUE
);

CREATE TABLE leads (
    id          serial PRIMARY KEY,
    source      text NOT NULL CHECK (source IN ('site', 'telegram', 'referral', 'ads')),
    manager_id  integer NOT NULL REFERENCES managers (id),
    amount      numeric(12, 2) NOT NULL CHECK (amount >= 0),
    created_at  timestamptz NOT NULL
);

-- история стадий: одна строка на каждый переход
CREATE TABLE stage_events (
    id       bigserial PRIMARY KEY,
    lead_id  integer NOT NULL REFERENCES leads (id) ON DELETE CASCADE,
    stage    text NOT NULL CHECK (stage IN ('new', 'qualified', 'proposal', 'won', 'lost')),
    at       timestamptz NOT NULL,
    UNIQUE (lead_id, stage)
);

CREATE INDEX leads_created_at_idx ON leads (created_at);
CREATE INDEX leads_manager_idx ON leads (manager_id);
CREATE INDEX stage_events_lead_idx ON stage_events (lead_id, at);

CREATE TABLE IF NOT EXISTS admin
(
    admin_id INTEGER,
    username VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS queues_list
(
    id         INTEGER PRIMARY KEY,
    queue_name VARCHAR(255),
    start      INTEGER,
    admin_id   INTEGER REFERENCES admin (admin_id)
);

CREATE TABLE IF NOT EXISTS queue
(
    id REFERENCES queues_list (id),
    queuer_id   INTEGER,
    queuer_name VARCHAR(255)
);
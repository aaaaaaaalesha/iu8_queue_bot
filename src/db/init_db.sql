-- DROP TABLE IF EXISTS admin;
-- DROP TABLE IF EXISTS chat;
-- DROP TABLE IF EXISTS queue;

CREATE TABLE IF NOT EXISTS admin
(
    admin_id PRIMARY KEY,
    username VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS chat
(
    id          INTEGER PRIMARY KEY,
    assignee_id INTEGER REFERENCES admin (admin_id),
    chat_id     INTEGER,
    chat_title  VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS queue
(
    id          INTEGER PRIMARY KEY,
    assignee_id INTEGER REFERENCES admin (admin_id),
    queue_name  VARCHAR(255),
    start       TIMESTAMP,
    chat_id     INTEGER,
    chat_title  VARCHAR(255),
    msg_id      INTEGER UNIQUE NULL,
    msg_text    TEXT           NULL
);
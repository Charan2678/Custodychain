CREATE DATABASE IF NOT EXISTS custodychain;
USE custodychain;

CREATE TABLE IF NOT EXISTS evidence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    original_content TEXT NOT NULL,
    original_hash VARCHAR(64) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS handlers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    step_order INT NOT NULL
);

CREATE TABLE IF NOT EXISTS custody_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evidence_id INT NOT NULL,
    handler_id INT NOT NULL,
    hash_before VARCHAR(64) NOT NULL,
    hash_after VARCHAR(64) NOT NULL,
    actual_content_snapshot TEXT NOT NULL,
    status_declared VARCHAR(20) NOT NULL DEFAULT 'success',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evidence_id) REFERENCES evidence(id),
    FOREIGN KEY (handler_id) REFERENCES handlers(id)
);

CREATE TABLE IF NOT EXISTS verification_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    evidence_id INT NOT NULL,
    final_verdict VARCHAR(50) NOT NULL,
    broken_step_id INT NULL,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (evidence_id) REFERENCES evidence(id),
    FOREIGN KEY (broken_step_id) REFERENCES handlers(id)
);

-- Seed the 5 fixed handlers in pipeline order (only if empty)
INSERT INTO handlers (name, step_order)
SELECT * FROM (SELECT 'Collector', 1) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM handlers WHERE step_order = 1);

INSERT INTO handlers (name, step_order)
SELECT * FROM (SELECT 'Analyst Tool', 2) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM handlers WHERE step_order = 2);

INSERT INTO handlers (name, step_order)
SELECT * FROM (SELECT 'Export Tool', 3) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM handlers WHERE step_order = 3);

INSERT INTO handlers (name, step_order)
SELECT * FROM (SELECT 'Reviewer', 4) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM handlers WHERE step_order = 4);

INSERT INTO handlers (name, step_order)
SELECT * FROM (SELECT 'Archive', 5) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM handlers WHERE step_order = 5);

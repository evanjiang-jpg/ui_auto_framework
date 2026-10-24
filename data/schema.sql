-- ==============================================================
-- 演示用 sqlite 表结构与种子数据
-- 由 db fixture 在 sqlite 模式下自动执行，可重复执行（幂等）
-- 真实项目把本文件替换为自己的建表/初始化脚本，或直接置空
-- ==============================================================

CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT    NOT NULL UNIQUE,
    nickname TEXT    DEFAULT '',
    status   TEXT    DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    amount     REAL    DEFAULT 0,
    status     TEXT    DEFAULT 'created'
);

-- 种子数据（INSERT OR IGNORE 保证重复执行不报错）
INSERT OR IGNORE INTO users (id, username, nickname, status)
VALUES (1, 'demo_user', '演示用户', 'active');

INSERT OR IGNORE INTO orders (id, user_id, product_id, amount, status)
VALUES (1, 1, 1001, 99.0, 'paid');

"""为 created_at / crawled_at 补上数据库级默认值 CURRENT_TIMESTAMP

背景（为什么要单独写这个迁移）：
    Django 的 auto_now_add 只在**应用层**赋值，生成的列是 `datetime NOT NULL`，
    数据库层面并没有默认值。这意味着任何绕过 ORM 的裸 SQL INSERT
    只要不显式给出该列，就会直接报 "Field 'created_at' doesn't have a default value"。
    而设计文档中这两列的定义是 `DATETIME DEFAULT CURRENT_TIMESTAMP`（数据库自动填充）。

    Django 4.2 尚未提供 db_default 参数（该特性 5.0 才引入），
    因此只能通过 RunSQL 显式 ALTER。

注意：Django 的 RunSQL 一次只执行一条语句（PyMySQL 默认未开启
     CLIENT.MULTI_STATEMENTS），故拆成两个操作。
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tourism', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE tourism_stat "
                "MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ),
            reverse_sql=(
                "ALTER TABLE tourism_stat "
                "MODIFY COLUMN created_at DATETIME NOT NULL"
            ),
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE crawl_log "
                "MODIFY COLUMN crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ),
            reverse_sql=(
                "ALTER TABLE crawl_log "
                "MODIFY COLUMN crawled_at DATETIME NOT NULL"
            ),
        ),
    ]

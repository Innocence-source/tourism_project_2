"""项目主包。

在这里把 PyMySQL 伪装成 MySQLdb，使 Django 能够识别 MySQL 驱动。
必须在任何 Django 数据库相关代码加载之前执行，因此放在本包的 __init__.py。
"""
import pymysql

# 版本兼容补丁（必须在 install_as_MySQLdb() 之前完成）：
# Django 会校验 MySQLdb 客户端版本不低于 1.4.3，而 PyMySQL 上报的是
# (1, 2, 3, 'final', 0)，会被误判为「版本过低」并抛出 ImproperlyConfigured。
# 这里显式抬高 version_info 与 __version__，骗过版本校验。
# 该写法是 PyMySQL 官方 FAQ 推荐方案，不影响任何实际功能。
pymysql.version_info = (1, 4, 6, 'final', 0)
pymysql.__version__ = '1.4.6'

# 让 Django 内部的 `import MySQLdb` 实际拿到 PyMySQL
pymysql.install_as_MySQLdb()

"""
Django 全局配置 —— 全国旅游数据分析与可视化系统

涵盖：数据库(MySQL 8.0)、DRF、跨域(CORS)、时区、静态资源
说明：本项目为本科毕业设计，采用本地开发配置，不涉及生产部署安全加固。
"""
from pathlib import Path

# ============================================================
# 一、路径配置
# ============================================================
# BASE_DIR 指向 backend/ 目录（manage.py 所在目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 爬虫原始数据目录：backend/data/
DATA_DIR = BASE_DIR / 'data'

# ============================================================
# 二、安全配置
# ============================================================
# 开发用密钥，仅本地演示；正式部署必须改为环境变量注入
SECRET_KEY = 'django-insecure-tourism-graduation-project-dev-key-2026'

# 开发模式：开启后自动热重载、显示详细报错页
DEBUG = True

# 开发阶段允许任意 Host，避免 127.0.0.1 / localhost / 局域网 IP 访问被拦截
ALLOWED_HOSTS = ['*']

# ============================================================
# 三、应用注册
# ============================================================
INSTALLED_APPS = [
    # --- Django 内置应用 ---
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # --- 第三方应用 ---
    'rest_framework',        # Django REST Framework，提供 API 能力
    'corsheaders',           # 跨域请求支持

    # --- 业务应用（注意：使用 apps.xxx 全路径，apps 目录已随 backend 加入路径）---
    'apps.region',           # 地区维度：省份 / 城市
    'apps.tourism',          # 旅游统计数据
    'apps.crawler',          # 数据采集（management command）
    'apps.analysis',         # 数据分析聚合接口
]

# ============================================================
# 四、中间件
# ============================================================
MIDDLEWARE = [
    # CORS 中间件必须尽可能靠前，且必须在 CommonMiddleware 之前，
    # 否则跨域响应头可能被后续中间件覆盖掉。
    'corsheaders.middleware.CorsMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# 五、路由与 WSGI
# ============================================================
ROOT_URLCONF = 'tourism_project.urls'
WSGI_APPLICATION = 'tourism_project.wsgi.application'

# ============================================================
# 六、模板
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================
# 七、数据库配置（MySQL 8.0）
# ============================================================
# 数据库连接参数集中在此，方便统一修改。
# 密码优先级：环境变量 TOURISM_DB_PASSWORD > 下方默认值
import os

DB_NAME = 'tourism_db'
DB_USER = 'root'
DB_PASSWORD = os.environ.get('TOURISM_DB_PASSWORD', '')  # ← 本机 MySQL root 密码
DB_HOST = '127.0.0.1'
DB_PORT = '3306'

DATABASES = {
    'default': {
        # 驱动名依然写 mysql，因为项目 __init__.py 已把 PyMySQL 伪装为 MySQLdb
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tourism_db',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',           # 完整 UTF-8，支持 emoji
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        },
    }
}

# ============================================================
# 八、跨域配置（django-cors-headers）
# ============================================================
# 开发阶段直接放行所有来源，省去逐个添加 http://localhost:5173 的麻烦
CORS_ALLOW_ALL_ORIGINS = True

# 显式声明允许的来源，便于生产环境切换时保留
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# 允许携带 Cookie / 认证头
CORS_ALLOW_CREDENTIALS = True

# 允许的前端请求头
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================
# 九、DRF 配置
# ============================================================
REST_FRAMEWORK = {
    # 默认只返回 JSON 渲染器，避免浏览器直接访问接口时被 BrowsableAPI 的 HTML 干扰
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # 本项目接口为纯查询统计，无需认证；如需可改为 SessionAuthentication
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    # 统一时间格式
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}

# ============================================================
# 十、国际化与时区
# ============================================================
LANGUAGE_CODE = 'zh-hans'        # 后台管理界面显示中文
TIME_ZONE = 'Asia/Shanghai'      # 东八区
USE_I18N = True
# 关闭 UTC 存储，直接存本地时间，前端拿到的字符串即为北京时间，便于大屏展示
USE_TZ = False

# ============================================================
# 十一、静态资源
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # collectstatic 输出目录

# 主键类型：按数据库设计文档要求，
# region / city_ranking / crawl_log 主键为 INT，tourism_stat 为 BIGINT
# （tourism_stat 在模型中显式声明了 BigAutoField，其余走本默认值）
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# ============================================================
# 十二、日志（爬虫运行信息落盘，便于排查）
# ============================================================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'tourism.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

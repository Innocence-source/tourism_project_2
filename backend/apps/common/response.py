"""
统一 API 响应体
===============

全站所有接口的返回结构固定为：

    成功：{"code": 200, "msg": "success", "data": {...} | [...]}
    失败：{"code": 400, "msg": "错误原因", "data": null}

设计决策说明（重要，答辩可能被问）：
    业务错误一律使用 HTTP 200 + 业务 code 表达，而不是 HTTP 4xx/5xx。
    原因：前端 Axios 只需在 then 分支中判断 code 字段即可统一处理，
    不必区分 then/catch 两套逻辑；同时保证「返回格式统一」这一需求落地。
    真正的服务器异常（500）仍由 Django 兜底返回标准错误页。
"""
from rest_framework.response import Response

# 业务状态码
CODE_SUCCESS = 200
CODE_PARAM_ERROR = 400
CODE_NOT_FOUND = 404
CODE_SERVER_ERROR = 500


def api_ok(data=None, msg='success'):
    """成功响应。"""
    return Response({'code': CODE_SUCCESS, 'msg': msg, 'data': data})


def api_fail(msg, code=CODE_PARAM_ERROR, data=None):
    """业务失败响应（HTTP 状态码保持 200，用 body 中的 code 表意）。"""
    return Response({'code': code, 'msg': msg, 'data': data})


# ---------------------------------------------------------------
# 参数解析辅助
# ---------------------------------------------------------------
def parse_int(params, key, default=None, min_value=None, max_value=None):
    """从 query_params 中解析整数。

    :return: (值, 错误信息) —— 解析成功时错误信息为 None
    """
    raw = params.get(key)
    if raw is None or raw == '':
        if default is None:
            return None, None
        return default, None

    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, f'参数 {key} 必须为整数，当前值：{raw!r}'

    if min_value is not None and value < min_value:
        return None, f'参数 {key} 不能小于 {min_value}'
    if max_value is not None and value > max_value:
        return None, f'参数 {key} 不能大于 {max_value}'

    return value, None


def parse_str(params, key, default=None, choices=None):
    """从 query_params 中解析字符串，可限定候选值。

    :return: (值, 错误信息)
    """
    raw = params.get(key)
    if raw is None or raw == '':
        return default, None

    value = raw.strip()
    if choices and value not in choices:
        return None, f'参数 {key} 取值非法，可选：{", ".join(choices)}'

    return value, None

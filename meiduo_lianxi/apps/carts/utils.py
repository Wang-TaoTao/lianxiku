
import json

from utils.cookiesecret import CookieSecret




# 封装合并购物车
def merge_cart_cookie_to_redis(request,user,response):

    # 获取cookie购物车数据
    cookie_str = request.COOKIES.get('carts')

    # 如果cookie_str 没值 就直接响应结果
    if not cookie_str:
        return response

    # 如果有值 解密
    cookie_dict = CookieSecret.loads(cookie_str)

    # 获取redis购物车数据
    from django_redis import get_redis_connection
    # 连接
    redis_conn = get_redis_connection('carts')
    # 获取该用户所有购物车数据
    redis_data = redis_conn.hgetall(user.id)

    # 将redis数据转换成普通字典
    redis_dict = {}
    for key,value in redis_data.items():
        sku_id = int(key.decode())
        sku_value = json.loads(value.decode())
        redis_dict[sku_id] = sku_value

    # 合并购物车数据
    redis_dict.update(cookie_dict)

    # 修改redis中的数据
    for sku_id in redis_dict.keys():
        redis_conn.hset(user.id,sku_id,json.dumps(redis_dict[sku_id]))

    # 删除cookie的购物车数据
    response.delete_cookie('carts')

    # 响应结果
    return response
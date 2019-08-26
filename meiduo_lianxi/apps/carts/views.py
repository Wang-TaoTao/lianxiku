
import json

from django import http
from django.shortcuts import render
from django_redis import get_redis_connection


from django.views import View

from apps.goods.models import SKU
from utils.cookiesecret import CookieSecret
from utils.response_code import RETCODE






# 展示首页简单购物车
class CartsSimpleView(View):

    def get(self,request):

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 如果用户登录 操作redis
            # 连接redis
            redis_conn = get_redis_connection('carts')
            # 获取该用户所有购物车数据
            redis_data = redis_conn.hgetall(user.id)

            # 转换成普通字典
            carts_dict = {}
            for key,value in redis_data.items():
                sku_id = int(key.decode())
                sku_value = json.loads(value.decode())
                carts_dict[sku_id] = sku_value

        else:

            # 如果用户没登录 操作cookie
            # 获取cookie
            cookie_str = request.COOKIES.get('carts')
            # 判断
            if cookie_str:
                # 解密
                carts_dict = CookieSecret.loads(cookie_str)
            else:
                # 空字典
                carts_dict = {}

        cart_skus = []
        # 取出所有的键
        sku_ids = carts_dict.keys()
        # 查询所有商品
        skus = SKU.objects.filter(id__in = sku_ids)
        # 遍历所有商品 构造给前端的数据
        for sku in skus:
            cart_skus.append({
                'id':sku.id,
                'name':sku.name,
                'count':carts_dict.get(sku.id).get('count'),
                'default_image_url':sku.default_image.url,

            })
        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_skus': cart_skus})




# 全选购物车
class CartsSelectAllView(View):

    def put(self,request):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected')

        # 校验参数
        if selected:
            if not isinstance(selected,bool):
                return

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:

            # 登录 操作redis
            redis_conn = get_redis_connection('carts')
            # 获取当前用户所有数据
            redis_data = redis_conn.hgetall(user.id)

            # 转成普通字典 修改seletecd

            for key,value in redis_data.items():
                sku_id = int(key.decode())
                sku_value = json.loads(value.decode())
                sku_value["selected"] = selected
                # 写入数据
                redis_conn.hset(user.id,sku_id,json.dumps(sku_value))
            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '全选购物车成功'})

        else:
            # 没登录 操作cookie
            # 接收cookie
            cookie_str = request.COOKIES.get('carts')
            # 构造响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '全选购物车成功'})
            # 判断
            if cookie_str is not None:

                # 解密
                carts_dict = CookieSecret.loads(cookie_str)

                # 修改seleted
                for sku_id in carts_dict:
                    carts_dict[sku_id]['selected'] = selected

                # 加密
                cookie_sstr = CookieSecret.dumps(carts_dict)


                # 写入cookie
                response.set_cookie('carts',cookie_sstr,max_age=3600*15*24)
            # 响应结果
            return response





# 购物车 增删改查
class CartsView(View):

    # 增加购物车
    def post(self,request):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected',True)
        # 校验参数
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')
        try:
            count != int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count有误')
        if selected:
            if not isinstance(selected,bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:

            # 登录 操作redis
            redis_conn = get_redis_connection('carts')
            # 取出用户所有购物车数据
            redis_data = redis_conn.hgetall(user.id)
            # 如果没有购物车数据 则直接新增记录
            if not redis_data:
                redis_conn.hset(user.id,sku_id,json.dumps({"count":count,"selected":selected}))

            # 如果有购物车数据 ，就检查添加的商品是否已经在购物车中
            if str(sku_id).encode() in redis_data:
                # 如果在购物车中 就把该条商品的count提出来 加上 用户输入的count
                carts_dict = json.loads(redis_data[str(sku_id).encode()].decode())
                # 将相同商品的个数累加
                carts_dict['count'] = count
                # carts_dict['selected'] = selected
                # 更新数据
                redis_conn.hset(user.id, sku_id, json.dumps(carts_dict))

            # 如果该商品不在购物车中 ，则直接新增数量
            else:
                redis_conn.hset(user.id, sku_id, json.dumps({"count": count, "selected": selected}))

            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})

        else:
            # 没登录 操作cookie
            # 获取cookie_str
            cookie_str = request.COOKIES.get('carts')
            # 判断用户是否有购物车数据
            if cookie_str:
                # 解密
                carts_dict = CookieSecret.loads(cookie_str)
            else:
                # 空字典
                carts_dict = {}

            # 判断该商品是否在购物车中
            if sku_id in carts_dict:
                # 取出之前的count 再累加
                old_count = carts_dict[sku_id]['count']
                # 加上用户刚添加的
                count += old_count

            # 修改数据
            carts_dict[sku_id]={
                'count':count,
                'selected':selected,
            }
            # 加密
            cookie_sstr = CookieSecret.dumps(carts_dict)

            # 响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
            # 写入cookie
            response.set_cookie('carts',cookie_sstr,max_age = 3600*24*15)

            # 响应结果
            return response


    # 展示购物车
    def get(self,request):

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 登录 操作redis
            redis_conn = get_redis_connection('carts')
            # 取出该用户所有购物车数据
            redis_data = redis_conn.hgetall(user.id)

            # 转换格式
            carts_dict = {}
            for key,value in redis_data.items():
                sku_id = int(key.decode())
                sku_value = json.loads(value.decode())
                carts_dict[sku_id] = sku_value

        else:

            # 未登录 操作cookie
            # 取出cookie_str
            cookie_str = request.COOKIES.get('carts')
            # 判断是否有购物车数据
            if cookie_str:
                # 解密
                carts_dict = CookieSecret.loads(cookie_str)

            else:
                # 空字典
                carts_dict = {}

        # 取出所有的sku_id 键
        sku_ids = carts_dict.keys()
        # 构造前端需要的数据
        cart_skus = []
        # 取出当前商品信息
        skus = SKU.objects.filter(id__in = sku_ids)

        # 遍历取数据
        for sku in skus:
            cart_skus.append({

                'id': sku.id,
                'name': sku.name,
                'count': carts_dict.get(sku.id).get('count'),
                'selected': str(carts_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount': str(sku.price * carts_dict.get(sku.id).get('count')),
            })



        context = {
            'cart_skus':cart_skus,
        }

        return render(request,'cart.html',context)



    # 修改购物车
    def put(self,request):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected')
        # 校验参数
        if not all([sku_id,count]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            sku = SKU.objects.get(id = sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')
        try:
            count != int(count)
        except Exception as e:
            return http.HttpResponseForbidden('参数count有误')
        if selected:
            if not isinstance(selected,bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:

            # 登录 操作redis
            redis_conn = get_redis_connection('carts')
            # 修改购物车数据
            redis_conn.hset(user.id,sku_id,json.dumps({"count":count,"selected":selected}))


        else:

            # 未登录 操作cookie
            # 获取用户cookie
            cookie_str = request.COOKIES.get('carts')
            # 判断是否有值
            if cookie_str:
                # 解密
                carts_dict = CookieSecret.loads(cookie_str)
            else:
                # 空字典
                carts_dict = {}

            carts_dict[sku_id]={
                "count":count,
                "selected":selected,
            }
            # 加密
            cookie_sstr = CookieSecret.dumps(carts_dict)

        # 构造前端需要的数据
        cart_sku = {
            'id':sku.id,
            'count':count,
            'selected':selected,
            'name':sku.name,
            'default_iamge_url':sku.default_image.url,
            'price':sku.price,
            'amount':sku.price * count,

        }
        # 构造响应对象
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})
        # 如果是没有登录的用户 就写入cookie
        if not user.is_authenticated:
            response.set_cookie('carts',cookie_sstr,max_age=3600*24*15)

        # 响应结果
        return response



    # 删除购物车
    def delete(self,request):

        # 接收参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        # 校验参数
        try:
            sku = SKU.objects.get(id = sku_id)
        except SKU.DoesNotExist:
            return
        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:

            # 登录 操作redis
            redis_conn = get_redis_connection('carts')
            # 删除数据
            redis_conn.hdel(user.id,sku_id)

            # 响应结果
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})

        else:
            # 没登录 操作cookie
            cookie_str = request.COOKIES.get('carts')
            # 判断
            if cookie_str:
                # 解密
                carts_dict = CookieSecret.loads(cookie_str)
            else:
                # 空字典
                carts_dict = {}

            # 构造响应对象
            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})

            # 判断 如果该商品在购物车中 就删除
            if sku_id in carts_dict:
                # 删除
                del carts_dict[sku_id]
                # 加密
                cookie_sstr = CookieSecret.dumps(carts_dict)

                # 响应结果并将购物车数据写入cookie
                response.set_cookie('carts',cookie_sstr,max_age=3600*24*15)

            # 响应结果
            return response
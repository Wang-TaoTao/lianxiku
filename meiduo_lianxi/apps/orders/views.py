# orders视图
import json
from datetime import datetime

from decimal import Decimal
from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from apps.goods.models import SKU
from apps.orders.models import OrderInfo, OrderGoods
from apps.users.models import Address
from utils.response_code import RETCODE



# 展示提交成功界面
class OrderSuccessView(LoginRequiredMixin,View):

    def get(self,request):

        # 接受参数
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')


        # 构造前端需要的数据
        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        # 响应结果
        return render(request, 'order_success.html', context)




# 保存订单基本信息和订单商品信息
class OrderCommitView(LoginRequiredMixin,View):

    def post(self,request):


        # 接受参数
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        # 校验参数
        if not all([address_id,pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            address = Address.objects.get(id = address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id错误')
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'],OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')
        # 获取登录用户
        user = request.user
        # 生成订单编号
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        # ----------设置事务起点-----------
        with transaction.atomic():

            # ---------设置事务保存点----------
            save_id = transaction.savepoint()

            try:
                # 将信息保存到商品信息表中
                order = OrderInfo.objects.create(
                    order_id = order_id,
                    user = user,
                    address = address,
                    total_count = 0,
                    total_amount = Decimal('0'),
                    freight = Decimal('10.00'),
                    pay_method = pay_method,
                    status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY']
                    else OrderInfo.ORDER_STATUS_ENUM['UNSEND']

                )

                # 从redis中取出用户选中的购物车数据
                redis_conn = get_redis_connection('carts')
                redis_data = redis_conn.hgetall(user.id)

                carts_dict = {}
                for key, value in redis_data.items():
                    sku_id = int(key.decode())
                    sku_value = json.loads(value.decode())
                    if sku_value['selected']:
                        carts_dict[sku_id] = sku_value

                # 根据购物车数据遍历商品信息
                for sku_id in carts_dict.keys():

                    while True:

                        sku = SKU.objects.get(id=sku_id)

                        # 先求出最原始的库存量和销量
                        old_stock = sku.stock
                        old_sales = sku.sales

                        sku_count = carts_dict[sku_id]['count']
                        if sku_count > sku.stock:

                            # ----------设置事务回滚------------
                            transaction.savepoint_rollback(save_id)

                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})
                        #
                        # # 动态修改sku表的库存和销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()

                        # # 模拟资源竞争
                        # import time
                        # time.sleep(10)

                        # 使用乐观锁 修改sku表的库存和销量
                        new_stock = old_stock - sku_count
                        new_sales = old_sales + sku_count
                        result = SKU.objects.filter(id=sku_id,stock = old_stock).update(stock=new_stock,sales=new_sales)

                        # 如果下单失败,库存足够则继续下单,直到下单成功或者库存不足
                        if result == 0 :
                            continue

                        # 动态修改spu表的分类销量
                        sku.spu.sales += sku_count
                        sku.spu.save()
                        # 修改商品订单商品信息
                        OrderGoods.objects.create(
                            order = order,
                            sku = sku,
                            count = sku_count,
                            price = sku.price,


                        )

                        # 保存商品订单基本信息总价和总数量
                        order.total_count += sku_count
                        order.total_amount += (sku_count * sku.price)

                        # 下单成功 或 失败跳出
                        break

                # 动态修改总金额 + 运费
                order.total_amount += order.freight
                order.save()
            except:

                # -----------设置事务回滚-----------
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单失败'})

            # -----------提交事务-----------
            transaction.savepoint_commit(save_id)

        # 删除购物车中已结算的商品
        redis_conn.hdel(user.id,*carts_dict)
        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单成功', 'order_id': order.order_id})





# 结算订单页面
class OrderSettlementView(LoginRequiredMixin,View):


    def get(self,request):

        # 取出地址
        user = request.user
        try:
            address = Address.objects.filter(user=user,is_deleted=False)
        except Address.DoesNotExist:
            address = None
        # 从Redis中取出选中的购物车数据
        redis_conn = get_redis_connection('carts')
        redis_data = redis_conn.hgetall(user.id)

        carts_dict = {}
        for key,value in redis_data.items():
            sku_id = int(key.decode())
            sku_value = json.loads(value.decode())
            if sku_value['selected']:
                carts_dict[sku_id] = sku_value
        total_count = 0
        total_amount = Decimal(0.00)

        skus = SKU.objects.filter(id__in=carts_dict.keys())
        # 根据购物车数据遍历sku表
        for sku in skus:
            sku.count = carts_dict[sku.id]['count']
            sku.amount = sku.count * sku.price

            # 计算总金额和数量
            total_count += sku.count
            total_amount += (sku.count * sku.amount)

        # 加运费
        freight = Decimal('10.00')

        # 构造前端需要的数据
        context = {
            'addresses':address,
            'skus':skus,
            'total_count':total_count,
            'total_amount':total_amount,
            'freight':freight,
            'payment_amount':total_amount + freight,
            'default_address_id':user.default_address_id,


        }
        # 响应结果
        return render(request, 'place_order.html', context)
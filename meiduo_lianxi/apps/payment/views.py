import os

from alipay import AliPay
from django import http
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View



from apps.orders.models import OrderInfo
from apps.payment.models import Payment
from utils.response_code import RETCODE





# 保存支付宝订单支付结果 支付宝回调美多商城
class PaymentStatusView(LoginRequiredMixin,View):

    def get(self,request):

        # 接受参数
        query_dict = request.GET
        data = query_dict.dict()

        # 取出标签sign并删除
        signature = data.pop('sign')

        # 创建支付宝支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )
        # 确认这个重定向是alipay重定向过来的
        success = alipay.verify(data,signature)
        # 如果正确
        if success:

            # 获取订单编号
            order_id = data.get('out_trade_no')
            # 获取支付宝流水账号
            trade_id = data.get('trade_no')
            # 保存payment模型类信息
            Payment.objects.create(
                order_id = order_id,
                trade_id = trade_id,

            )
            # 修改订单状态
            OrderInfo.objects.filter(order_id=order_id,status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])


            # 响应trade_id
            context = {
                'trade_id': trade_id
            }
            return render(request, 'pay_success.html', context)

        else:
            # 订单支付失败，重定向到我的订单
            return http.HttpResponseForbidden('非法请求')



# 生成支付宝支付链接
class PaymentView(LoginRequiredMixin,View):

    def get(self,request,order_id):

        # 查询要支付的订单
        user = request.user

        try:
            order = OrderInfo.objects.get(user=user,order_id=order_id,status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])

        except:
            return http.HttpResponseForbidden('订单信息错误')

        # 创建支付宝支付对象
        alipay = AliPay(
            appid = settings.ALIPAY_APPID,
            app_notify_url = None,
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'keys/app_private_key.pem'),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'keys/alipay_public_key.pem'),
            sign_type="RSA2",
            debug= settings.ALIPAY_DEBUG,

        )

        # 生成支付宝支付链接
        order_string = alipay.api_alipay_trade_page_pay(
            subject = "美多商城%s" % order_id,
            out_trade_no = order_id,
            total_amount = str(order.total_amount),
            return_url=settings.ALIPAY_RETURN_URL,
            notify_url=None,

        )

        # 拼接链接
        alipay_url = settings.ALIPAY_URL + '?' + order_string

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})

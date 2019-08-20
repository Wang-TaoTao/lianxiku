# verifications 视图函数


from django import http
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View


# 校验图形验证码
from apps.verifications import constants
from meiduo_lianxi.settings.dev import logger
from utils.response_code import RETCODE


class SMSCodeView(View):

    def get(self,request,mobile):
        # 接收参数
        uuid = request.GET.get('image_code_id')
        image_code = request.GET.get('image_code')
        print("---------------")
        print("图片 uuid",uuid)
        print("---------------")
        print("用户输入验证码内容",image_code)
        print("---------------")

        # 和图片验证码redis连接取uuid
        from django_redis import get_redis_connection
        image_redis_client = get_redis_connection('verify_image_code')
        redis_img_code = image_redis_client.get(uuid)

        # 校验
        if redis_img_code is None:
            return JsonResponse({'code':"4001",'errmsg':"图形验证码失效了"})
        # 删除
        try:
            image_redis_client.delete(uuid)

        except Exception as e:
            logger.error(e)

        # 将用户输入图片验证码和Redis中的验证码进行对比
        if image_code.lower() != redis_img_code.decode().lower():

            return JsonResponse({'code':'4001','errmsg':'输入图形验证码有误'})


        # 生成短信验证码,在redis中存储
        from random import randint
        sms_code = "%06d" % randint(0,999999)
        sms_code_redis = get_redis_connection('sms_code')


        # 判断发送短信是否频繁
        send_flag = sms_code_redis.get('send_flag_%s' % mobile )
        if send_flag:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '发送短信过于频繁'})

        # 创建redis管道
        p1 = sms_code_redis.pipeline()
        # 保存短信验证码
        p1.setex('sms_%s' % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 重新写入send_flag
        p1.setex('send_flag_%s' % mobile,constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行管道请求
        p1.execute()

        # 让第三方 容联云 发送短信
        # from libs.yuntongxun.sms import CCP
        # CCP().send_template_sms(mobile,[sms_code,5],1)

        # 实现异步发送短信
        from celery_tasks.sms.tasks import ccp_send_sms_code
        ccp_send_sms_code(mobile,sms_code)

        print("当前手机验证码是:",sms_code)

        # 响应前端结果
        return http.JsonResponse({'code': '0', 'errmsg': '发送短信成功'})

# 图形验证码
class ImageCodeView(View):

    def get(self,request,uuid):

        # 生成图片验证码
        from libs.captcha.captcha import captcha
        text ,image =captcha.generate_captcha()

        # 保存图片验证码
        from django_redis import get_redis_connection
        redis_client = get_redis_connection('verify_image_code')
        redis_client.setex(uuid,300,text)

        # 响应图形验证码
        return http.HttpResponse(image,content_type = 'image/jpeg')


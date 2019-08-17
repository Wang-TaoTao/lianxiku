# verifications 视图函数


from django import http
from django.shortcuts import render
from django.views import View


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


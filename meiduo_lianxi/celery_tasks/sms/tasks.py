

from celery_tasks.main import app

# 定义任务
@app.task
def ccp_send_sms_code(mobile, sms_code):
    """
    发送短信异步任务
    :param mobile: 手机号
    :param sms_code: 短信验证码
    :return: 成功0 或 失败-1
    """
    from libs.yuntongxun.sms import CCP
    send_result = CCP().send_template_sms(mobile, [sms_code, 5], 1)
    print("当前验证码是:", sms_code)
    return send_result
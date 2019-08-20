import re

from django.conf import settings
from django.contrib.auth.backends import ModelBackend

from apps.users.models import User



# 定义生成邮箱验证链接方法
def generate_verify_email_url(user):
    """
    :param user: 用户对象
    :return:
    """
    # 1.加密的数据
    data_dict = {'user_id': user.id, "email": user.email}

    # 2. 进行加密数据
    from utils.secret import SecretOauth
    secret_data = SecretOauth().dumps(data_dict)

    # 3. 返回拼接url
    active_url = settings.EMAIL_ACTIVE_URL + '?token=' + secret_data
    return active_url




# 提取手机号或用户名
def get_user_by_account(account):

    '''根据account查询用户'''

    try:
        if re.match(r'^^1[3-9]\d{9}$',account):

            # 说明是手机号登录
            user = User.objects.get(mobile=account)
        else:
            # 说明是用户名登录
            user = User.objects.get(username=account)

    except User.DoesNotExist:
        return None
    else:
        return user




# 自定义用户认证后端
class UsernameMobileAuthBackend(ModelBackend):

    # 重写authenticate方法
    def authenticate(self, request, username=None, password=None, **kwargs):

        # 根据传入的username获取user对象，username可以是手机号也可以是用户名
        user = get_user_by_account(username)

        # 校验user是否存在并且校验密码是否正确
        if user and user.check_password(password):

            return user
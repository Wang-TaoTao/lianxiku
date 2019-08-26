import base64
import pickle



class CookieSecret(object):
    # 加密
    @classmethod
    def dumps(cls, data):
        # 1.将数据装换成bytes
        data_bytes = pickle.dumps(data)
        # 2.将bytes使用base64序列化加密
        base64_bytes = base64.b64encode(data_bytes)
        # 3.将加密完毕的bytes以字符串类型输出
        base64_str = base64_bytes.decode()

        return base64_str

    # 解密
    @classmethod
    def loads(cls, data):
        # 1.将数据解密转成bytes
        base64_bytes = base64.b64decode(data)
        # 2.将bytes转回原来的python类型
        pickle_data = pickle.loads(base64_bytes)

        return pickle_data

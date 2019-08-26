



# 封装面包屑组件
def get_breadcrumb(cat3):

    # 通过三级分类获取二级
    cat2 = cat3.parent
    # 通过二级分类获取一级
    cat1 = cat2.parent

    # 构造前端需要的数据
    breadcrumb = {
        'cat1': {
            # 根据一级分类关联频道获取频道的url
            'url': cat1.goodschannel_set.all()[0].url,
            'name': cat1.name,
        },
        'cat2': cat2,
        'cat3': cat3,
    }

    return breadcrumb
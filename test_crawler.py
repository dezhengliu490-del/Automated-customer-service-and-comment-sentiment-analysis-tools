#导入自动化模块
import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

# 1. 实例化配置对象
co = ChromiumOptions()

# 2. 手动设置浏览器路径 (请将下面的路径替换为你刚才复制的实际路径)
# 注意：路径前的 r 是为了防止转义字符错误
browser_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
co.set_browser_path(browser_path)

# 3. 传入配置对象并打开浏览器
dp = ChromiumPage(addr_or_opts=co)

# 接下来的代码保持不变
dp.get('https://item.jd.com/10167235203199.html')
#访问网站
dp.get('https://item.jd.com/10167235203199.html')
#等待加载
time.sleep(2)
#监听数据包
dp.listen.start('getLegoWareDetailComment')
#下滑页面
dp.scroll.to_bottom()
#自动点击打开评论页面（元素定位）
dp.ele('css:#comment-root > div.all-btn').click()
#等待数据包加载
resp = dp.listen.wait()
#获取响应的数据内容
json_data = resp.response.body
print("获取到API响应数据")

#提取评论列表
if json_data and 'commentInfoList' in json_data:
    comments = json_data['commentInfoList']
    print(f"找到 {len(comments)} 条评论")
    
    #循环遍历，提取列表里面的元素
    for index in comments:
        #提取具体每条评论保存字典中
        dit = {
            '昵称': index.get('userNickName', '未知用户'),
            '评分': index.get('commentScore', 0),
            '评论内容': index.get('commentData', ''),
            '点赞数': index.get('praiseCnt', 0),
            '回复数': index.get('replyCnt', 0),
            '产品型号': '',
            '产品颜色': '',
            '发布地区': index.get('publishArea', ''),
            '评论时间': index.get('commentDate', '')
        }
        print("\n提取到的评论:")
        print(dit)
else:
    print("没有找到评论列表")
    print("响应数据的键:", list(json_data.keys()) if json_data else "无数据")




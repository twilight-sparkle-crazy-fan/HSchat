import re
import os
import requests
from flask import Flask, render_template, request, jsonify

# 配置 Flask 使用 'images' 文件夹作为静态文件目录
app = Flask(__name__, static_folder='images')

# 假设你的图片存放在 images/ 文件夹下
IMAGE_FOLDER = 'images/'

# 定义 headers
headers = {
    'accept': 'application/json',
    'Authorization': 'application-666786f48b334cd1086300c2497cca18'  # API Key
}


# 获取 profile id
def get_profile_id():
    profile_url = 'http://localhost:8080/api/application/profile'  # 自己的 URL
    response = requests.get(profile_url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['id']
    else:
        print("获取 profile id 失败")
        return None


# 获取 chat id
def get_chat_id(profile_id):
    chat_open_url = f'http://localhost:8080/api/application/{profile_id}/chat/open'  # 改为自己的 URL
    response = requests.get(chat_open_url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        print("获取 chat id 失败")
        return None


# 发送聊天消息
def send_chat_message(chat_id, payload):
    chat_message_url = f'http://localhost:8080/api/application/chat_message/{chat_id}'
    response = requests.post(chat_message_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"发送消息失败，状态码: {response.status_code}")
        return None


# 主函数，处理消息
def get_chat_response(message, re_chat=False, stream=False):
    profile_id = get_profile_id()
    if profile_id:
        chat_id = get_chat_id(profile_id)
        if chat_id:
            chat_message_payload = {
                "message": message,
                "re_chat": re_chat,
                "stream": stream
            }
            response = send_chat_message(chat_id, chat_message_payload)
            if response:
                content = response['data']['content']
                # 在返回的内容中查找专利号并生成图片路径
                response_with_images = add_images_to_response(content)
                return response_with_images
    return "Error: Unable to get a response from the API."


# 正则表达式匹配专利号
def find_patent_numbers(text):
    # 改进后的正则表达式
    pattern = r'CN\d{9}[A-Z]'
    return re.findall(pattern, text)


# 根据专利号生成图片标签，并将专利号后添加图片
def add_images_to_response(text):
    """
    遍历文本中的专利号，插入对应图片标签，并在每次插入图片后添加换行。
    """
    result = ""  # 用于存储更新后的文本
    last_pos = 0  # 记录上一段处理的结束位置

    # 查找单个专利号并插入图片标签
    for match in re.finditer(r'CN\d{9}[A-Z]', text):
        patent_number = match.group(0)  # 获取当前匹配到的专利号
        start, end = match.span()  # 获取匹配位置
        result += text[last_pos:start]  # 添加当前专利号前的文本
        last_pos = end  # 更新处理位置

        # 检查对应图片是否存在
        image_path = os.path.join(IMAGE_FOLDER, f"{patent_number}.png")
        if os.path.exists(image_path):
            # 如果图片存在，生成图片标签并添加换行
            image_tag = f"<br><img src='/images/{patent_number}.png' alt='{patent_number}' style='max-width: 100%; height: auto;'><br>"
            result += f"{patent_number}{image_tag}"
        else:
            # 如果图片不存在，仅添加专利号
            result += patent_number

    # 添加剩余的文本
    result += text[last_pos:]
    return result


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_message = request.form["user_message"]
        response = get_chat_response(user_message)  # 获取聊天响应
        return jsonify({"response": response})  # 返回响应给前端

    return render_template("index2.html")  # 渲染主页


if __name__ == "__main__":
    app.run(debug=True)

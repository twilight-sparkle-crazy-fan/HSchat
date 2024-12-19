import re
import os
import random
import base64
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from transformers.utils.versions import require_version
from flask_cors import CORS  # 添加跨域支持

require_version("openai>=1.5.0", "To fix: pip install openai>=1.5.0")

app = Flask(__name__, static_folder='pictures')


CORS(app)  # 启用跨域资源共享

PICTURES_FOLDER = 'pictures/'  # 本地图片文件夹路径

# 确保 pictures 文件夹存在
os.makedirs(PICTURES_FOLDER, exist_ok=True)

# 原有的 headers
headers = {
    'accept': 'application/json',
    'Authorization': 'application-666786f48b334cd1086300c2497cca18'
}

def encode_image(image_path):
    """将本地图片转换为base64编码"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_local_multimodal_response(message, image_path=None):
    """调用本地多模态模型（7861端口）"""
    client = OpenAI(
        api_key="0",
        base_url="http://localhost:7861/v1",
    )

    messages = [{"role": "user", "content": [{"type": "text", "text": message}]}]
    
    # 如果有图片，添加图片
    if image_path:
        image_url = f"data:image/jpeg;base64,{encode_image(image_path)}"
        messages[0]["content"].append({"type": "image_url", "image_url": {"url": image_url}})

    result = client.chat.completions.create(
        messages=messages, 
        model="test"
    )

    return result.choices[0].message.content

def get_profile_id():
    """获取 profile id"""
    profile_url = 'http://localhost:8080/api/application/profile'
    response = requests.get(profile_url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['id']
    else:
        print("获取 profile id 失败")
        return None

def get_chat_id(profile_id):
    """获取 chat id"""
    chat_open_url = f'http://localhost:8080/api/application/{profile_id}/chat/open'
    response = requests.get(chat_open_url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']
    else:
        print("获取 chat id 失败")
        return None

def send_chat_message(chat_id, payload):
    """发送聊天消息"""
    chat_message_url = f'http://localhost:8080/api/application/chat_message/{chat_id}'
    response = requests.post(chat_message_url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"发送消息失败，状态码: {response.status_code}")
        return None

def get_chat_response(message, image_path=None):
    """获取聊天响应，根据是否有图片选择不同的模型"""
    if image_path:
        return get_local_multimodal_response(message, image_path)
    
    profile_id = get_profile_id()
    if profile_id:
        chat_id = get_chat_id(profile_id)
        if chat_id:
            chat_message_payload = {
                "message": message,
                "re_chat": False,
                "stream": False
            }
            response = send_chat_message(chat_id, chat_message_payload)
            if response:
                content = response['data']['content']
                response_with_images = add_images_to_response(content)
                return response_with_images
    return "Error: Unable to get a response from the API."

def find_patent_numbers(text):
    """查找专利号"""
    pattern = r'CN\d{9}[A-Z]'
    return re.findall(pattern, text)

def add_images_to_response(text):
    """遍历文本中的专利号，插入对应图片标签"""
    result = ""
    last_pos = 0
    for match in re.finditer(r'CN\d{9}[A-Z]', text):
        patent_number = match.group(0)
        start, end = match.span()
        result += text[last_pos:start]
        last_pos = end
        image_path = os.path.join(PICTURES_FOLDER, f"{patent_number}.png")
        if os.path.exists(image_path):
            image_tag = f"<br><img src='/pictures/{patent_number}.png' alt='{patent_number}' style='max-width: 100%; height: auto;'><br>"
            result += f"{patent_number}{image_tag}"
        else:
            result += patent_number
    result += text[last_pos:]
    return result

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_message = request.form["user_message"]
        image_path = None

        # 处理随机图片关键词
        keywords = [
            "请提供一些类似的花洒专利图",
            "能否给我一些相似的花洒专利图",
            # 更多关键词...
        ]

        if any(keyword in user_message for keyword in keywords):
            # 获取所有图片文件，排除robot.png和user.png
            image_files = [f for f in os.listdir(PICTURES_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg')) and f not in ['robot.png', 'user.png']]
            if len(image_files) >= 2:
                selected_images = random.sample(image_files, 2)
                image_tags = (
                    "<div style='display: flex; justify-content: center; align-items: center;'>" +
                    ''.join(
                        f"<img src='/pictures/{image}' alt='类似的花洒专利图片' style='width: 300px; height: 300px; object-fit: contain; margin: 10px;'>"
                        for image in selected_images
                    ) +
                    "</div>"
                )
                response = f"好的，我将在下面给出一些类似的专利图片：<br>{image_tags}"
                return jsonify({"response": response})
            else:
                return jsonify({"response": "图片文件夹中图片数量不足，无法提供随机图片"})

        # 检查是否上传了图片
        if 'image' in request.files and request.files['image'].filename != '':
            image = request.files['image']
            image_path = os.path.join(PICTURES_FOLDER, 'temp_upload.png')
            image.save(image_path)

        response = get_chat_response(user_message, image_path)
        return jsonify({"response": response})
    return render_template("index2.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
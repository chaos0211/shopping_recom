import json
import time
from tencentcloud.asr.v20190614 import asr_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

# === ✅ 替换为你自己的腾讯云 API 密钥 ===
SECRET_ID = "AKIDnSuPhoiPtNeiZCev2wfCaliRxHOHxQfh"
SECRET_KEY = "sZ3JMBm9MQIxPdeS3QbaMvGNHySkpiRm"

# ✅ 替换为你的公网音频链接（必须为 HTTPS）
AUDIO_URL = "https://ttt-1367100332.cos.ap-guangzhou.myqcloud.com/pt.mp3"


# ✅ 语音识别模型（普通话用 16k_zh，粤语用 16k_yue）
ENGINE_MODEL = "16k_zh"

# === 初始化客户端 ===
cred = credential.Credential(SECRET_ID, SECRET_KEY)
http_profile = HttpProfile()
http_profile.endpoint = "asr.tencentcloudapi.com"
client_profile = ClientProfile()
client_profile.httpProfile = http_profile
client = asr_client.AsrClient(cred, "ap-shanghai", client_profile)

import base64
import requests

# 下载音频并转 base64（仅当 SourceType 为 1 且需提供 Data 时）
audio_base64 = ""
if AUDIO_URL.startswith("http"):
    audio_content = requests.get(AUDIO_URL).content
    audio_base64 = base64.b64encode(audio_content).decode("utf-8")

task_params = {
    "EngineModelType": ENGINE_MODEL,
    "ChannelNum": 1,
    "ResTextFormat": 0,
    "SourceType": 1,
    "Url": AUDIO_URL,
    "Data": audio_base64
}
create_req = models.CreateRecTaskRequest()
create_req.from_json_string(json.dumps(task_params))
# ✅ 调试输出
print("📤 正在创建识别任务...")
print(f"SourceType: {create_req.SourceType}")
print(f"Url: {create_req.Url}")

# === 发起任务请求 ===
create_resp = client.CreateRecTask(create_req)
task_id = json.loads(create_resp.to_json_string())["Data"]["TaskId"]
print(f"✅ 任务已创建，TaskId：{task_id}")

# === 查询识别任务状态 ===
status_req = models.DescribeTaskStatusRequest()
status_req.TaskId = task_id

print("⏳ 等待识别结果中...")
while True:
    status_resp = client.DescribeTaskStatus(status_req)
    status_data = json.loads(status_resp.to_json_string())
    status = status_data["Data"]["StatusStr"]

    if status == "success":
        result_text = status_data["Data"]["Result"]
        print("✅ 转写完成，以下是结果（前500字）：\n")
        print(result_text[:500] + ("..." if len(result_text) > 500 else ""))
        with open("transcribed_text.txt", "w", encoding="utf-8") as f:
            f.write(result_text)
        print("\n📄 已保存到 transcribed_text.txt")
        break
    elif status == "failed":
        print("❌ 识别失败")
        break
    else:
        print(f"⌛ 当前状态：{status}，请稍候...")
        time.sleep(5)
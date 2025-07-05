import edge_tts
import asyncio
from pydub import AudioSegment
import re
import os
from pathlib import Path

# 读取原始文本
with open("tts.txt", encoding="utf-8") as f:
    content = f.read()

# 正则匹配时间戳和音乐标签
time_pattern = r"\b(\d{1,2}):(\d{2})\b"
music_pattern = r"\[music\]-\[(.*?)\]"

parts = []
last_pos = 0

for match in re.finditer(f"{time_pattern}|{music_pattern}", content):
    start, end = match.span()
    text_part = content[last_pos:start].strip()
    if text_part:
        parts.append({"type": "text", "content": text_part})
    if match.group(1) and match.group(2):  # 匹配时间
        minutes, seconds = int(match.group(1)), int(match.group(2))
        parts.append({"type": "pause", "duration": minutes * 60 + seconds})
    elif match.group(3):  # 匹配音乐
        music_file = match.group(3)
        parts.append({"type": "music", "filename": music_file})
    last_pos = end

final_part = content[last_pos:].strip()
if final_part:
    parts.append({"type": "text", "content": final_part})

# 设置语音参数
voice = "zh-HK-HiuMaanNeural"
rate = "-20%"

# 生成语音片段
async def generate_segment(part, index):
    filename = f"segment_{index}.mp3"
    communicate = edge_tts.Communicate(part, voice=voice, rate=rate)
    await communicate.save(filename)
    return filename

# 主函数
async def main():
    audio = AudioSegment.empty()
    idx = 0
    for part in parts:
        if part["type"] == "text":
            temp_file = await generate_segment(part["content"], idx)
            segment = AudioSegment.from_file(temp_file)
            audio += segment
            os.remove(temp_file)
            idx += 1
        elif part["type"] == "pause":
            silence = AudioSegment.silent(duration=part["duration"] * 1000)
            audio += silence
        elif part["type"] == "music":
            music_path = Path(part["filename"])
            if music_path.exists():
                music_segment = AudioSegment.from_file(music_path)
                audio += music_segment
            else:
                print(f"⚠️ 未找到音乐文件：{part['filename']}，已跳过。")
    audio.export("output_with_music.mp3", format="mp3")
    print("✅ 生成成功：output_with_music.mp3")

# 运行
asyncio.run(main())
from pydub import AudioSegment

# 加载原始背景音乐
bgm = AudioSegment.from_file("backmu.mp3")

# 截取前22秒（单位为毫秒）
bgm_22s = bgm[:22 * 1000]

# 导出为新文件
bgm_22s.export("backmu_22s.mp3", format="mp3")

print("已成功截取前22秒并保存为 backmu_22s.mp3")
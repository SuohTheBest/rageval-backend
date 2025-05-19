from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps
import random
import os
from tqdm import tqdm

# 设置路径
raw_data_dir = Path("raw")
output_dir = Path("t_dataset")
train_dir = output_dir / "train"
val_dir = output_dir / "val"

# 创建输出目录
for subdir in [train_dir, val_dir]:
    subdir.mkdir(parents=True, exist_ok=True)

# 背景颜色备选
background_colors = [
    (255, 255, 255),  # 白色
    (0, 0, 0),        # 黑色
    (255, 0, 0),      # 红色
    (0, 255, 0),      # 绿色
    (0, 0, 255),      # 蓝色
    (255, 255, 0),    # 黄色
    (255, 165, 0),    # 橙色
]

# 添加渐变背景生成函数
def create_gradient_background(size=(128, 128)):
    colors = random.sample(background_colors, 2)
    gradient = Image.new("RGB", size)
    for y in range(size[1]):
        r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * y / size[1])
        g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * y / size[1])
        b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * y / size[1])
        gradient.paste((r, g, b), (0, y, size[0], y + 1))
    return gradient

def augment_image(img: Image.Image, size=(128, 128)):
    # 随机旋转
    angle = random.uniform(-15, 15)  # 旋转角度范围
    img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255, 0))

    # 随机缩放
    scale = random.uniform(0.7, 1.3)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.BICUBIC)

    # 背景填充
    if random.random() < 0.3:  # 50% 概率选择纯色背景
        bg_color = random.choice(background_colors)
        background = Image.new("RGBA", size, bg_color + (255,))
    else:  # 50% 概率选择渐变背景
        background = create_gradient_background(size)

    offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
    background.paste(img, offset, img)

    # 颜色增强
    background = ImageEnhance.Color(background).enhance(random.uniform(0.8, 1.2))
    background = ImageEnhance.Brightness(background).enhance(random.uniform(0.8, 1.2))
    background = ImageEnhance.Contrast(background).enhance(random.uniform(0.8, 1.2))

    return background.convert("RGB")

samples_per_class = 80   # 每类生成图像数量
val_ratio = 0.1          # 验证集占比

# 在主循环前添加类别统计
class_dirs = [d for d in raw_data_dir.iterdir() if d.is_dir()]
total_classes = len(class_dirs)

# 使用 tqdm 包装外层循环
for class_dir in tqdm(class_dirs, desc="处理类别", unit="类"):
    if not class_dir.is_dir():
        continue
    class_name = class_dir.name
    images = list(class_dir.glob("*.png"))
    if not images:
        continue

    # 使用 tqdm 包装内层循环
    for i in tqdm(range(samples_per_class), 
                 desc=f"生成 {class_name} 的增强图像",
                 unit="张",
                 leave=False):  # leave=False 使得内层进度条完成后消失
        img_path = random.choice(images)
        img = Image.open(img_path).convert("RGBA")
        aug_img = augment_image(img)

        subset = val_dir if random.random() < val_ratio else train_dir
        save_path = subset / class_name
        save_path.mkdir(parents=True, exist_ok=True)
        aug_img.save(save_path / f"{i}.jpg")
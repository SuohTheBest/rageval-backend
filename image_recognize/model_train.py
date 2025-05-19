from ultralytics import YOLO

# 定义训练参数
model_path = "yolov8m-cls.pt"  # 预训练模型路径
data_path = "t_dataset"        # 数据集路径
epochs = 50                    # 训练轮数777
imgsz = 128                    # 图片尺寸
batch = 64                     # 批量大小
augment = True                 # 是否启用数据增强
lr0 = 1e-3                     # 初始学习率
lrf = 0.1                      # 学习率衰减因子
weight_decay = 0.0005          # 权重衰减
patience = 10                  # 早停的耐心值
project = "yolo_model"         # 项目保存路径
name = "yolo_model"            # 模型名称

# 加载预训练模型
model = YOLO(model_path)

# 训练模型
results = model.train(
    data=data_path,
    epochs=epochs,
    imgsz=imgsz,
    batch=batch,
    augment=augment,
    lr0=lr0,
    lrf=lrf,
    weight_decay=weight_decay,
    patience=patience,
    project=project,
    name=name
)

# 打印训练结果
print(results)
import os

def delete_aug_images(directory):
    # 遍历目录及其子目录
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查文件是否以'aug_'开头且以'.png'结尾
            if file.startswith('aug_') and file.endswith('.png'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"已删除: {file_path}")
                except Exception as e:
                    print(f"删除失败 {file_path}: {str(e)}")

if __name__ == "__main__":
    dataset_path = "dataset/val"  # 指定数据集路径
    delete_aug_images(dataset_path)
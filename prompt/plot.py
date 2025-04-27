import os
import re
from datetime import datetime

from models.Task import PromptEvaluation
from models.database import SessionLocal
import matplotlib.pyplot as plt


def get_prompt_plot(task_id ,method):
    db = SessionLocal()
    try:
        evals = (db.query(PromptEvaluation)
                 .filter(PromptEvaluation.task_id == task_id)
                 .filter(PromptEvaluation.method == method)
                 .order_by(PromptEvaluation.id.asc())
                 .all()
                 )

        x_values = []
        y_values = []
        length = len(evals)
        for i in range(length):
            match = re.search(r"[评估分数：(\d+)/10]",evals[i].output_text)
            if match:
                x_values.append(i+1)
                y_values.append(int(match.group(0)))

        import matplotlib.pyplot as plt

        # 设置中文字体（根据系统选择）
        plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows
        # plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # Mac
        # plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP']  # Linux

        # 解决负号显示问题
        plt.rcParams['axes.unicode_minus'] = False

        plt.figure(figsize=(10,5))
        plt.plot(
            x_values,y_values,
            marker='o',
            linestyle='-',
            color='steelblue',
            label='score'
        )

        plt.title(f"Prompt评估分数 - 指标: {method}",fontsize=14)
        plt.xlabel("评估轮数", fontsize=12)
        plt.ylabel("分数(/10)", fontsize=12)
        plt.xticks(x_values)  # 显示所有x刻度
        plt.ylim(0, 10)  # y轴范围固定为0-10
        plt.grid(alpha=0.4)
        plt.legend()

        plt.tight_layout()

        # TODO: 设置保存路径
        # 创建保存目录（如果不存在）
        save_dir = "eval_plots"
        os.makedirs(save_dir, exist_ok=True)

        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_plot_{task_id}_{method}_{timestamp}.png"
        save_path = os.path.join(save_dir, filename)

        # 保存图片（dpi=300 提高分辨率）
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")

        # plt.show()
        return save_path

    finally:
        db.close()

# if __name__ == "__main__":
#     get_prompt_plot(1,"扩展性")




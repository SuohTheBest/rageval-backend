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
        for index,eval in enumerate(evals):
            match = re.search(r"评估分数：(\d+)/10",eval.output_text)
            if match:
                x_values.append(index)
                y_values.append(int(match.group(1)))

        plt.figure(figsize=(10,5))
        plt.plot(
            x_values,y_values,
            marker='o',
            lineStyles='-',
            color='steelblue',
            label='评估分数'
        )

        plt.title("Prompt评估分数变化趋势",font_size=14)
        plt.xlabel("评估序号", fontsize=12)
        plt.ylabel("分数（/10）", fontsize=12)
        plt.xticks(x_values)  # 显示所有x刻度
        plt.ylim(0, 10)  # y轴范围固定为0-10
        plt.grid(alpha=0.4)
        plt.legend()

        plt.tight_layout()

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


        plt.show()

    finally:
        db.close()

# if __name__ == "__main__":
#     get_prompt_plot(1,"扩展性")




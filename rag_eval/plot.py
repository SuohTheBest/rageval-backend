import os
import re
from datetime import datetime

from models.Task import RAGEvaluation, TaskPlot
from models.database import SessionLocal
import matplotlib.pyplot as plt
def get_rag_plot(task_id,method):
    db = SessionLocal()
    try:
        
        evals = (db.query(RAGEvaluation)
                 .filter(RAGEvaluation.task_id == task_id)
                 .filter(RAGEvaluation.method == method)
                 .order_by(RAGEvaluation.id.asc())
                 .all()
                 )
        print("plot here")
        x_values = []
        y_values = []
        length = len(evals)
        for i in range(length):
            match = evals[i].output_text
            x_values.append(i+1)
            y_values.append(match)
        print(x_values)
        print(y_values)
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
        plt.ylim(0, 1)  # y轴范围固定为0-10
        plt.grid(alpha=0.4)
        plt.legend()

        plt.tight_layout()

        # 创建保存目录（如果不存在）
        save_dir = "eval_plots"
        os.makedirs(save_dir, exist_ok=True)

        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_rag_{task_id}_{method}_{timestamp}.png"
        save_path = os.path.join(save_dir, filename)

        # 保存图片（dpi=300 提高分辨率）
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")

        curr_prompt_plot = TaskPlot(task_id=task_id, method=method, link=filename)
        db.add(curr_prompt_plot)
        db.commit()
        # plt.show()
        return filename
    finally:
        db.close()
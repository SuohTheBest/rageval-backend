from typing import List
import re
import opencc


class MarkdownProcessor:
    """
    处理Markdown格式字符串的类。
    """

    def __init__(self):
        """
        初始化MarkdownProcessor，包括OpenCC转换器。
        """
        self.converter = opencc.OpenCC("t2s.json")  # 初始化OpenCC转换器，繁体到简体

    def __get_heading_level(self, line_text: str) -> int:
        """获取Markdown标题行级别"""
        match = re.match(r"^(#+)\s+", line_text)
        return len(match.group(1)) if match else 0

    def __get_heading_title(self, line_text: str) -> str:
        """获取Markdown标题行标题内容"""
        match = re.match(r"^(#+)\s+(.*)", line_text)
        return match.group(2).strip() if match else ""

    def _format_process(self, markdown_content: str) -> str:
        """
        格式处理。
        1. 如果一个列表行为单独一行，则将其转换为纯文本
        2. 若一行内容中包含超过3个英文分号，则在每个英文分号后添加换行（最后一个除外）
        3. 标题为“聲音”或“声音”及其所属内容删除
        """
        lines = markdown_content.splitlines()
        # 删除“聲音”或“声音”部分
        lines_after_removal = []  # type: List[str]
        is_deleting_section = False
        for line in lines:
            current_line_heading_level = self.__get_heading_level(line)
            if current_line_heading_level > 0:
                current_title = self.__get_heading_title(line)
                is_deleting_section = current_title in ["聲音", "声音"]
            if not is_deleting_section:
                lines_after_removal.append(line)

        processed_lines_final = []
        num_lines = len(lines_after_removal)
        for i, current_line_text in enumerate(lines_after_removal):
            current_line_content = current_line_text

            # 列表项转换
            if current_line_text.startswith("- "):
                prev_line_ok = i == 0 or lines_after_removal[i - 1].startswith("- ")
                next_line_ok = i == num_lines - 1 or lines_after_removal[
                    i + 1
                ].startswith("- ")

                if not (prev_line_ok or next_line_ok):
                    current_line_content = current_line_text[2:]

            # 分号处理
            semicolon_count = current_line_content.count(";")
            if semicolon_count > 3:
                current_line_content = ";\n".join(current_line_content.split(";"))
                if current_line_content.endswith("\n"):
                    current_line_content = current_line_content[:-1]

            processed_lines_final.append(current_line_content)

        return "\n".join(processed_lines_final)

    def _content_process(self, formatted_content: str) -> str:
        """
        内容处理。
        1. 删除空的括号对
        2. 删除不可渲染字符
        3. 使用OpenCC将繁体中文转换为简体中文
        """
        content = formatted_content

        # 1. 删除空的括号对
        content = re.sub(r"\(\s*\)", "", content)  # 删除 ()
        content = re.sub(r"（\s*）", "", content)  # 删除 （）
        content = re.sub(r"\[\s*\]", "", content)  # 删除 []
        content = re.sub(r"【\s*】", "", content)  # 删除 【】
        content = re.sub(r"\{\s*\}", "", content)  # 删除 {}

        # 2. 删除不可渲染字符
        content = re.sub(r"\\x[0-9a-fA-F]{2}", "", content)
        content = re.sub(r"\\u[0-9a-fA-F]{4}", "", content)

        # 3. 使用OpenCC将繁体中文转换为简体中文
        content = self.converter.convert(content)

        return content

    def __hard_split(self, content: str) -> List[str]:
        """
        硬划分内容。当单行超过500个字符时，也对该行进行拆分。
        """
        # 内容划分
        lines = content.splitlines()
        split_content = []
        current_content = []
        current_length = 0

        for line in lines:
            # 如果单行超过500字符，需要拆分这一行
            if len(line) > 500:
                # 先处理之前累积的内容
                if current_content:
                    split_content.append("\n".join(current_content))
                    current_content = []
                    current_length = 0

                # 拆分长行
                start = 0
                while start < len(line):
                    chunk = line[start : start + 300]
                    split_content.append(chunk)
                    start += 300
            else:
                # 检查添加当前行是否会导致块超过300字符
                if current_length + len(line) < 300:
                    current_content.append(line)
                    current_length += len(line)
                else:
                    if current_content:
                        split_content.append("\n".join(current_content))
                    current_content = [line]
                    current_length = len(line)

        # 处理最后剩余的内容
        if current_content:
            split_content.append("\n".join(current_content))

        return split_content

    def __split_recursive(self, content: str, head: str, level: int) -> List[str]:
        """
        递归划分内容。
        """
        # 内容划分
        lines = content.splitlines()
        split_content = []
        current_content = []
        for line in lines:
            if self.__get_heading_level(line) == level:
                if current_content:
                    split_content.append("\n".join(current_content))
                current_content = [line]
            else:
                current_content.append(line)
        if current_content:
            split_content.append("\n".join(current_content))

        # 内容大小处理
        processed_content = []
        cur_block_accumulator = ""
        for block_segment in split_content:
            can_accumulate = False
            if not cur_block_accumulator:
                # 如果累加器为空，并且当前段落足够小以开始累加
                if len(block_segment) <= 300:
                    cur_block_accumulator = block_segment
                    can_accumulate = True
            # 如果累加器非空，并且加上当前段落（和换行符）后仍足够小
            elif len(cur_block_accumulator) + len(block_segment) <= 300:
                cur_block_accumulator += "\n" + block_segment
                can_accumulate = True

            if can_accumulate:
                continue  # 成功累加或开始累加，处理下一个段落

            # 如果无法累加当前段落，则先处理（添加）已累积的内容
            if cur_block_accumulator:
                processed_content.append(cur_block_accumulator)
                cur_block_accumulator = ""  # 重置累加器

            # 现在处理当前段落 block_segment 本身
            if len(block_segment) < 300:
                # 它无法被追加（因为会超出长度），但它本身是小的，成为新的累加起点
                cur_block_accumulator = block_segment
            elif (
                len(block_segment) <= 500
            ):  # 明确包含300和500的边界情况 (300 <= len <= 500)
                processed_content.append(block_segment)
            else:  # len(block_segment) > 500
                sub_blocks = []
                if len(split_content) > 1 and level < 6:
                    block_lines = block_segment.splitlines()
                    if block_lines:  # 确保 block_lines 非空
                        block_head_line = block_lines[0]
                        block_actual_content = "\n".join(block_lines[1:])
                        sub_blocks = self.__split_recursive(
                            block_actual_content, block_head_line, level + 1
                        )
                    else:  # block_segment 长度大于500但 splitlines 为空（罕见情况）
                        sub_blocks = self.__hard_split(block_segment)
                else:
                    sub_blocks = self.__hard_split(block_segment)
                processed_content.extend(sub_blocks)

        # 处理循环结束后剩余的累积内容
        if cur_block_accumulator:
            processed_content.append(cur_block_accumulator)

        # 添加标头
        final_blocks_with_head = []
        if head:  # 仅当 head 非空时添加
            for p_block in processed_content:
                final_blocks_with_head.append(head + "\n" + p_block)
        else:
            final_blocks_with_head.extend(processed_content)

        return final_blocks_with_head

    def _content_split(self, processed_content: str) -> List[str]:
        """
        内容划分。
        """
        return self.__split_recursive(processed_content, "", 1)

    def process(self, markdown_text: str) -> List[str]:
        """
        处理Markdown字符串的主方法。

        Args:
            markdown_text: 输入的Markdown格式字符串。

        Returns:
            一个字符串列表。
        """
        formatted_text = self._format_process(markdown_text)
        processed_text = self._content_process(formatted_text)
        split_content = self._content_split(processed_text)
        return split_content


if __name__ == "__main__":
    with open("output.md", "r", encoding="utf-8") as f:
        markdown_data = f.read()
    processor = MarkdownProcessor()
    processed_markdown = processor.process(markdown_data)
    with open("output_processed.md", "w", encoding="utf-8") as f:
        f.write(("\n" + "-" * 50 + "\n").join(processed_markdown))

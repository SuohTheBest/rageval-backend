from markitdown import MarkItDown


class PdfConverter:
    """
    一个用于将 PDF 文件转换为 Markdown 字符串的工具类。
    """

    @staticmethod
    def convert(pdf_path: str) -> str:
        """
        将指定的 PDF 文件转换为 Markdown 字符串。

        参数:
            pdf_path (str): PDF 文件的路径。

        返回:
            str: 转换后的 Markdown 字符串。
        """
        converter = MarkItDown()
        markdown_string = converter.convert(pdf_path)
        return markdown_string


if __name__ == "__main__":
    example_pdf_path = "data/knowledge_library/conda.html"
    markdown_output = PdfConverter.convert(example_pdf_path)
    print(f"\nMarkdown output for '{example_pdf_path}':\n")
    print(markdown_output)

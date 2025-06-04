from markitdown import MarkItDown


class PdfToMarkdownConverter:
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
        return markdown_string.markdown


if __name__ == "__main__":
    example_pdf_path = "data\\knowledge_library\\test.pdf"
    markdown_output = PdfToMarkdownConverter.convert(example_pdf_path)
    with open("test.md", "w", encoding="utf-8") as f:
        f.write(markdown_output)

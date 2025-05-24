import json
from typing import Any, List, Dict, Union


class JsonToMarkdownConverter:
    """
    A class to convert JSON data to Markdown format.
    Keys from JSON objects are converted to Markdown headings based on nesting level.
    JSON arrays are converted to Markdown unordered lists.
    """

    @staticmethod
    def _to_markdown_recursive(data: Any, level: int) -> List[str]:
        """
        Recursively processes JSON data and converts it to Markdown lines.

        Args:
            data: The JSON data element (dict, list, str, int, float, bool, None).
            level: The current nesting level, used for heading depth for keys.

        Returns:
            A list of strings, where each string is a line of Markdown.
        """
        lines: List[str] = []
        level = min(level, 6)

        if isinstance(data, dict):
            for key, value in data.items():
                lines.append(f"{'#' * level} {key}")
                value_lines = JsonToMarkdownConverter._to_markdown_recursive(
                    value, level + 1
                )
                lines.extend(value_lines)

        elif isinstance(data, list):
            if len(data) == 1:
                # If the list has only one item, treat it as a single value
                item_md_lines = JsonToMarkdownConverter._to_markdown_recursive(
                    data[0], level
                )
                if item_md_lines:
                    lines.extend(item_md_lines)
            else:
                for item in data:
                    item_md_lines = JsonToMarkdownConverter._to_markdown_recursive(
                        item, level
                    )
                    lines.extend(
                        [
                            (
                                f"- {sub_line}"
                                if not sub_line.startswith("#")
                                else sub_line
                            )
                            for sub_line in item_md_lines
                        ]
                    )
        elif isinstance(data, bool):
            lines.append(str(data).lower())  # "true" or "false"
        elif isinstance(data, (str, int, float)):
            lines.append(str(data))

        return lines

    @staticmethod
    def convert(json_file_path: str) -> str:
        """
        Converts JSON data from a file to Markdown.

        Args:
            json_file_path: The path to the JSON file.

        Returns:
            A string containing the Markdown representation of the JSON data.
            Returns an error message string if JSON parsing fails or input type is invalid.
        """
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data_to_process = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: The file {json_file_path} was not found.")
        except json.JSONDecodeError:
            raise ValueError(
                f"Error: Could not decode JSON from the file {json_file_path}."
            )
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")

        if not isinstance(data_to_process, (dict, list)):
            raise ValueError("JSON content must be a dict or list.")

        if isinstance(data_to_process, list):
            all_md_lines: List[str] = []
            for item in data_to_process:
                item_md_lines = JsonToMarkdownConverter._to_markdown_recursive(item, 1)
                all_md_lines.extend(item_md_lines)
            return "\n".join(all_md_lines).strip()
        else:
            markdown_lines = JsonToMarkdownConverter._to_markdown_recursive(
                data_to_process, 1
            )
            return "\n".join(markdown_lines).strip()


if __name__ == "__main__":
    json_file_path = "data/knowledge_library/terrariawiki_terenemies.json"
    try:
        markdown_output = JsonToMarkdownConverter.convert(json_file_path)
        with open("output.md", "w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"Successfully converted {json_file_path} to output.md")
    except Exception as e:
        print(f"An error occurred: {e}")

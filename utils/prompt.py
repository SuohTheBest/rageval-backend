from dataclasses import dataclass
import typing as t
from llm import MRagasLLM
from pydantic import BaseModel

InputModel = t.TypeVar("InputModel", bound=BaseModel)
OutputModel = t.TypeVar("OutputModel", bound=BaseModel)


@dataclass
class PromptSchema:
    """
    Schema for the prompt.
    """

    input_model: InputModel  # type: ignore
    output_model: OutputModel  # type: ignore


class MRagasPrompt:
    """
    Abstract class for prompts.
    """

    def __init__(
        self,
        llm: MRagasLLM,
        prompt_schema: t.List[PromptSchema],
        specific_instruction: str,
        max_retries: int = 3,
    ):
        """
        Initializes the MRagasPrompt with an LLM and a prompt schema.
        Args:
            llm (MRagasLLM): The LLM to be used for evaluation.
            prompt_schema (List[PromptSchema]): The schema for the prompt.
            specific_instruction (str): The specific instruction for the LLM.
            max_retries (int): The maximum number of retries for generating output.
        """
        if len(prompt_schema) == 0:
            raise ValueError("The prompt schema is empty.")
        self.llm = llm
        self.prompt_schema = prompt_schema
        self.input_model = type(prompt_schema[0].input_model)
        self.output_model = type(prompt_schema[0].output_model)
        self.specific_instruction = specific_instruction
        self.max_retries = max_retries
        self.instruction = self._set_instruction()

    def _set_instruction(self):
        """
        Set the instruction for the LLM.
        """
        instruction = (
            "You will provide evaluations for other natural language models. "
            "Your specific task will be:\n"
            f"**{self.specific_instruction}**\n"
            "You will get the input in a JSON format that complies with the "
            "following schema as specified in JSON Schema:\n"
            f"{self.input_model.model_json_schema()}\n"
            "---\n"
            "Please return the output in a JSON format that complies with the "
            "following schema as specified in JSON Schema:\n"
            f"{self.output_model.model_json_schema()}\n"
            "Note: Do not use single quotes in your response but double quotes, "
            "properly escaped with a backslash.\n"
            "**Node**: Do not include any other text in your response, just the JSON.\n"
            "---\n"
            "Here are examples of the input and output:\n"
        )
        for prompt in self.prompt_schema:
            instruction += (
                f"Input:\n{prompt.input_model.model_dump_json()}\n"
                f"Output:\n{prompt.output_model.model_dump_json()}\n"
            )
        return instruction

    def generate(self, input_data: InputModel) -> OutputModel:  # type: ignore
        """
        Generate the output using the LLM.
        """
        if not isinstance(input_data, self.input_model):
            raise ValueError(
                f"Input data must be of type {self.input_model.__name__}, "
                f"but got {type(input_data).__name__}."
            )
        self.llm.set_instruction(self.instruction)
        response = self.llm.generate(input_data.model_dump_json())
        for try_count in range(self.max_retries):
            try:
                output_data = self.output_model.model_validate_json(response)
                return output_data  # type: ignore
            except Exception as e:
                if try_count == self.max_retries - 1:
                    raise e
                response = self.llm.generate(
                    input_data.model_dump_json(), force_retry=True
                )

import typing as t
import pandas as pd
from abc import ABC, abstractmethod


class SingleSample:
    def __init__(self, data: t.Dict[str, t.Any]):
        self.data = data

    def get_atributes(self) -> t.List[str]:
        """
        Returns the keys of the data.
        """
        return list(self.data.keys())

    def __getitem__(self, key: str) -> t.Any:
        """
        Returns the value associated with the key.
        """
        if key not in self.data:
            raise KeyError(f"Key '{key}' not found in the data.")
        return self.data[key]

    def pretty_repr(self) -> str:
        """
        Returns a pretty representation of the data.
        """
        return "\n".join(f"{key}: {value}" for key, value in self.data.items())


class DataSet:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    @classmethod
    def from_samples(cls, samples: t.List[SingleSample]) -> "DataSet":
        """
        Creates a DataSet from a list of SingleSample objects.
        """
        if not samples:
            raise ValueError("The list of samples is empty.")
        if not all(isinstance(sample, SingleSample) for sample in samples):
            raise ValueError(
                "All items in the list must be SingleSample instances.")
        data = pd.DataFrame([sample.data for sample in samples])
        return cls(data)

    def __getitem__(self, idx: int) -> SingleSample:
        """
        Returns a SingleSample object at the specified index.
        """
        if idx < 0 or idx >= len(self.data):
            raise IndexError("Index out of range.")
        return SingleSample(self.data.iloc[idx].to_dict())

    def __len__(self) -> int:
        """
        Returns the number of samples in the DataSet.
        """
        return len(self.data)

    def __iter__(self) -> t.Iterator[SingleSample]:
        """
        Returns an iterator over the DataSet.
        """
        for idx in range(len(self)):
            yield self[idx]

    def __add__(self, other: "DataSet") -> "DataSet":
        """
        Combines two DataSet objects.
        """
        if not isinstance(other, DataSet):
            raise ValueError("Can only add DataSet objects.")
        combined_data = pd.concat([self.data, other.data], ignore_index=True)
        return DataSet(combined_data)

    def get_shape(self) -> t.Tuple[int, int]:
        """
        Returns the shape of the DataFrame.
        """
        return self.data.shape

    def get_atributes(self) -> t.List[str]:
        """
        Returns the columns of the DataFrame.
        """
        return self.data.columns.tolist()

    def add_row(self, row: SingleSample) -> None:
        """
        Adds a row to the DataFrame.
        """
        if not isinstance(row, SingleSample):
            raise ValueError("row must be an instance of SingleSample.")
        if not self.get_atributes() == row.get_atributes():
            raise ValueError("Row attributes do not match DataFrame columns.")
        self.data = pd.concat(
            [self.data, pd.DataFrame([row.data])], ignore_index=True)

    def pretty_repr(self) -> str:
        """
        Returns a pretty representation of the DataFrame.
        """
        info = f"DataFrame Shape: {self.data.shape}, Total Entries: {self.data.size}\n"
        repr_str = "\n".join(
            f"Row {idx}:\n" +
            "\n".join(f"  {col}: {val}" for col, val in row.items())
            for idx, row in self.data.iterrows()
        )
        return info + repr_str

    def to_dict(self) -> t.List[t.Dict[str, t.Any]]:
        """
        Converts the DataFrame to a dictionary.
        """
        return [
            {str(k): v for k, v in row.items()}
            for row in self.data.to_dict(orient="records")
        ]


class CSVReader:
    @classmethod
    def read_csv(cls, file_path: str) -> DataSet:
        """
        Reads a CSV file and returns a DataSet object.
        """
        try:
            data = pd.read_csv(file_path)
            return DataSet(data)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"The file at path '{file_path}' was not found.")


class EvaluationResult(ABC):
    """
    Abstract class for evaluation results.
    This class is used to represent the results of an evaluation metric.
    It contains methods to combine results from multiple evaluations and
    to retrieve the evaluation metrics.
    """

    def __init__(self, dataSet: DataSet, scores: t.List[t.Dict[str, t.Any]]):
        """
        Initializes the EvaluationResult with a DataSet and scores.
        Args:
            dataSet (DataSet): The dataset used for evaluation.
            scores (List[Dict[str, Any]]): The scores obtained from the evaluation.
        """
        if not isinstance(dataSet, DataSet):
            raise ValueError("dataSet must be an instance of DataSet.")
        if not isinstance(scores, list):
            raise ValueError("scores must be a list of dictionaries.")
        self.dataSet = dataSet
        self.scores = scores
        if len(scores) == 0:
            raise ValueError("Scores cannot be empty.")

    def get_metrics(self) -> t.List[str]:
        """
        Returns the evaluation metrics.
        """
        if not self.scores:
            raise ValueError("No scores available.")
        return list(self.scores[0].keys())

    def __add__(self, other: "EvaluationResult") -> "EvaluationResult":
        """
        Adds two EvaluationResult objects together.
        """
        if not isinstance(other, EvaluationResult):
            raise ValueError("Can only add EvaluationResult objects.")
        if self.get_metrics() != other.get_metrics():
            raise ValueError("Metrics do not match.")

        combined_scores = self.scores + other.scores
        combined_dataSet = self.dataSet + other.dataSet
        return type(self)(combined_dataSet, combined_scores)

    @abstractmethod
    def get_results(self):
        """
        Returns the evaluation results.
        """
        pass

    @abstractmethod
    def pretty_repr(self) -> str:
        """
        Returns a pretty representation of the evaluation results.
        """
        pass

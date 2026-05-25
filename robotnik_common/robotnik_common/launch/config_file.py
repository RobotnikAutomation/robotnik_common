from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional
from typing import Union

import yaml
from launch import LaunchContext
from launch import SomeSubstitutionsType
from launch import SomeSubstitutionsType_types_tuple
from launch.frontend.parse_substitution import parse_substitution
from launch.substitution import Substitution
from launch.substitutions import SubstitutionFailure
from launch.utilities import normalize_to_list_of_substitutions
from launch.utilities import perform_substitutions
from launch.utilities.typing_file_path import FilePath


class ConfigFile(Substitution):
    """Evaluate substitutions in a YAML file and return a temporary config path."""

    def __init__(
        self,
        param_file: Union[FilePath, SomeSubstitutionsType],
    ) -> None:
        self.__evaluated_param_file: Optional[Path] = None
        self.__created_tmp_file = False

        self.__param_file = param_file
        if isinstance(param_file, SomeSubstitutionsType_types_tuple):
            self.__param_file = normalize_to_list_of_substitutions(param_file)  # type: ignore

    def perform(self, context: LaunchContext) -> str:
        """Substitute the parameter file path."""
        param_file = self.__param_file
        if isinstance(param_file, list):
            param_file = perform_substitutions(context, self.__param_file)  # type: ignore

        param_file_path: Path = Path(param_file)  # type: ignore
        with open(param_file_path, 'r') as input_file, NamedTemporaryFile(
            mode='w', prefix='launch_params_', delete=False
        ) as temp_file:
            parsed = perform_substitutions(
                context,
                parse_substitution(input_file.read()),
            )  # type: ignore
            try:
                yaml.safe_load(parsed)
            except Exception as exc:
                raise SubstitutionFailure(
                    'The substituted parameter file is not a valid yaml file'
                ) from exc
            temp_file.write(parsed)
            param_file_path = Path(temp_file.name)
            self.__created_tmp_file = True

        self.__evaluated_param_file = param_file_path
        return str(param_file_path)

    def cleanup(self) -> None:
        """Remove the temporary file if it was created."""
        if self.__created_tmp_file and self.__evaluated_param_file is not None:
            try:
                self.__evaluated_param_file.unlink()
            except FileNotFoundError:
                pass
            self.__evaluated_param_file = None

    def __del__(self):
        self.cleanup()

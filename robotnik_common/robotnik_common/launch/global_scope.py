# Copyright (c) 2023, Robotnik Automation S.L.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Robotnik Automation S.L.L. nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Robotnik Automation S.L.L. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import warnings
import re
import inspect
from launch.substitutions import EnvironmentVariable, TextSubstitution
from launch.substitutions import LaunchConfiguration
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument

RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class GlobalScope:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalScope, cls).__new__(cls)
            cls._instance._declared_args = []
            cls._instance._declare_args_origins = {}
            cls._instance._declare_params = {}
        return cls._instance

    def globalScope(self, name, env=None, default=None):
        
        if env==None and default==None:
            raise RuntimeError(
                f"{RED}[GlobalScope ERROR] Variable '{name}' was declared without a "
                f"value{RESET}"
            )

        if env!=None and default!=None:
            raise RuntimeError(
                f"{RED}[GlobalScope ERROR] Variable '{name}' cannot be defined with "
                f"'env' and 'default' parameters at the same time{RESET}"
            )


        if name in self._declare_params:
            warnings.warn(
                (
                    f"{YELLOW}[GlobalScope] Ignoring '{name}' declaration because was "
                    f"already declared in '{self._declare_args_origins[name]}'{RESET}"
                ),
                stacklevel=2
            )

        else:

            if default is not None:

                # Manage $(var variable) format
                pattern = r"\$\((?:var )(\w+)\)(.*)"
                match = re.match(pattern, default)

                if match:
                    var_name = match.group(1)
                    suffix = match.group(2)

                    if var_name not in self._declare_params:
                        raise RuntimeError(
                            f"{RED}[GlobalScope ERROR] Variable '{var_name}' used in '{name}' "
                            f"is not declared.{RESET}"
                        )

                    default = [
                        self._declare_params[var_name],
                        TextSubstitution(text=suffix)
                    ]
            

            if env is not None:
                declare_arg = DeclareLaunchArgument(
                    name, default_value=EnvironmentVariable(env, default_value=default))
            else:
                declare_arg = DeclareLaunchArgument(name, default_value=default)


            self._declared_args.append(declare_arg)

            caller_frame = inspect.stack()[1]
            caller_filename = caller_frame.filename
            self._declare_args_origins[name] = caller_filename

            config = LaunchConfiguration(name)
            self._declare_params[name] = config


        return self._declare_params[name]

    def getArgs(self):
        return self._declared_args

    def getParams(self):
        return self._declare_params.copy()

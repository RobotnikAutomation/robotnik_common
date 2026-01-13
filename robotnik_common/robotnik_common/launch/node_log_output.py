from launch_ros.actions import Node
import launch
import re
from datetime import datetime
from launch.actions import RegisterEventHandler
from launch.event import Event
from launch.event_handlers import OnProcessIO
from typing import Optional
from random import randint

def RNode(use_custom_logger : bool = True, *args, **kwargs) -> list[Node, Optional[RegisterEventHandler]]:
    """
    Creates a Node with an optional custom logger event handler for enhanced log output formatting.
    Adds color-coded node names, timestamps, and log levels to the console output.
    Args:
        use_custom_logger (bool): If True, attaches the custom logger event handler. Default is True.
        *args, **kwargs: Arguments passed to the Node constructor.
    Returns:
        list: A list containing the Node and optionally the RegisterEventHandler for logging.
    """
    if not use_custom_logger:
        return [Node(*args, **kwargs)]

    kwargs["output"] = "log"
    node = Node(*args, **kwargs)
    return [node, RobotnikCustomLogger(node)]

class RobotnikCustomLogger(RegisterEventHandler):
    """
    Custom logger event handler for enhanced ROS 2 node log output formatting.
    
    Formats log messages with color-coded node names, timestamps, and log levels
    to provide visual clarity for easier debugging and monitoring in the console.

    Inherits from RegisterEventHandler to handle process IO events from ROS 2 nodes.
    
    Args:
        node (Node): The ROS 2 node to attach the logger to.
    
    Attributes:
        BG_COLORS (list[str]): ANSI background color codes for node name highlighting.
        RESET (str): ANSI reset code to clear formatting.
        NODE_WIDTH (int): Fixed width for the highlighted node name block (default: 20).
        PID_WIDTH (int): Fixed width for the PID block (default: 10).
        LOGTYPE_WIDTH (int): Fixed width for the log level (default: 5).
        LOG_LEVEL_RE (re.Pattern): Regex to match log levels [DEBUG|INFO|WARN|ERROR|FATAL|TRACE].
        TIMESTAMP_RE (re.Pattern): Regex to match ROS timestamps [seconds.nanoseconds].
        NODE_NAME_RE (re.Pattern): Regex to match node names in format [node_name]:.
        ANSI_ESCAPE (re.Pattern): Regex to detect and strip ANSI escape codes.
    
    Methods:
        _on_stdout(event): Handles stdout events, parses and formats log output.
        _on_stderr(event): Handles stderr events (currently redirects to _on_stdout).
        _parse_ros_log_line(line): Parses a single ROS log line into structured components.
        _parse_ros_log_lines(lines): Parses multiple log lines.
        _get_and_remove_log_level(line): Extracts and removes log level from line.
        _get_and_remove_node_name(line): Extracts and removes node name from line.
        _get_and_remove_timestamp(line): Extracts and removes timestamp from line.
        _remove_match_from_line(line, match): Removes a regex match from line.
        _get_log_level_formatted(level): Returns formatted log level string.
        _get_timestamp_formatted(timestamp): Converts ROS timestamp to readable format.
        _get_name_and_pid_formatted(name, pid, color): Returns color-highlighted name/PID block.
        _format_log(parsed, pid): Formats parsed log components into final output string.
        _reduce_consecutive_spaces(text): Collapses multiple spaces to single space.
        _highlight_block(text, width, color): Applies background color to text block.
        _get_color_for_pid(pid): Selects consistent color based on process ID.
    """
    BG_COLORS = [
        "\033[48;5;52m",   # dark red
        "\033[48;5;88m",   # red
        "\033[48;5;124m",  # bright red
        "\033[48;5;28m",   # green
        "\033[48;5;34m",   # bright green
        "\033[48;5;22m",   # dark green
        "\033[48;5;94m",   # brown
        "\033[48;5;130m",  # orange
        "\033[48;5;214m",  # yellow
        "\033[48;5;220m",  # bright yellow
        "\033[48;5;18m",   # dark blue
        "\033[48;5;19m",   # blue
        "\033[48;5;27m",   # bright blue
        "\033[48;5;54m",   # purple
        "\033[48;5;55m",   # magenta
        "\033[48;5;90m",   # dark magenta
        "\033[48;5;30m",   # cyan
        "\033[48;5;37m",   # bright cyan
        "\033[48;5;240m",  # dark gray
        "\033[48;5;244m",  # gray
        "\033[48;5;250m",  # light gray
    ]

    RESET = "\033[0m"

    NODE_WIDTH = 20  # ancho fijo para nodo sombreado
    PID_WIDTH = 10    # ancho fijo para PID si no se extrae nombre del log
    LOGTYPE_WIDTH = 5  # ancho fijo para tipo de log

    LOG_LEVEL_RE = re.compile(r'\[(DEBUG|INFO|WARN|ERROR|FATAL|TRACE)\]', re.IGNORECASE)
    TIMESTAMP_RE = re.compile(r'\[\d+\.\d+\]')  # e.g. [1767962265.161910501]
    NODE_NAME_RE = re.compile(r'\[([A-Za-z0-9_.\-\/]+)\]:')
    ANSI_ESCAPE = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')

    def __init__(self, node: Node):
        super().__init__(
            OnProcessIO
            (
                target_action=node,
                on_stdout=self._on_stdout,
                on_stderr=self._on_stderr,
            )
        )
    
    def _parse_ros_log_lines(self, lines: str) -> list[dict]:
        parsed_lines = []
        for line in lines.splitlines():
            parsed = self._parse_ros_log_line(line)
            parsed_lines.append(parsed)
        return parsed_lines
    
    def _get_and_remove_log_level(self, line: str) -> tuple[str, str]:
        log_level_match = self.LOG_LEVEL_RE.search(line)
        log_level = None
        if log_level_match:
            log_level = log_level_match.group(1).upper()
            # Remove it from line
            line = self._remove_match_from_line(line, log_level_match)
        return log_level, line

    def _get_and_remove_node_name(self, line: str) -> tuple[str, str]:
        node_name_match = self.NODE_NAME_RE.search(line)
        node_name = None
        if node_name_match:
            node_name = node_name_match.group(1)
            # Remove it from line
            line = self._remove_match_from_line(line, node_name_match)
        return node_name, line

    def _get_and_remove_timestamp(self, line: str) -> tuple[str, str]:
        timestamp_match = self.TIMESTAMP_RE.search(line)
        timestamp = None
        if timestamp_match:
            timestamp_raw = timestamp_match.group(0).strip('[]')
            # Convert ROS time float string to datetime or just keep as is
            # For now, keep as string
            timestamp = timestamp_raw
            # Remove it from line
            line = self._remove_match_from_line(line, timestamp_match)
        return timestamp, line

    def _remove_match_from_line(self, line: str, match: re.Match) -> str:
        if match:
            return line[:match.start()] + line[match.end():].strip()
        return line

    def _parse_ros_log_line(self, line: str) -> dict:
        show_original = False
        # Find all ANSI codes and their positions
        ansi_codes = self.ANSI_ESCAPE.findall(line)
        # Remove all ANSI codes temporarily
        line_clean = self.ANSI_ESCAPE.sub('', line)
        # Strip spaces from clean text
        line_stripped = line_clean.strip()

        # Extract log level
        log_level, line_stripped = self._get_and_remove_log_level(line_stripped)

        # Extract timestamp
        timestamp, line_stripped = self._get_and_remove_timestamp(line_stripped)

        # Extract node name
        node_name, line_stripped = self._get_and_remove_node_name(line_stripped)

        show_original = node_name is None and log_level is None and timestamp is None

        # Remaining line_stripped is the message (strip leading/trailing spaces)
        message = line_stripped.strip()

        parsed_line_info = {}
        parsed_line_info["log_level"] = log_level
        parsed_line_info["timestamp"] = timestamp
        parsed_line_info["node_name"] = node_name
        parsed_line_info["message"] = message
        parsed_line_info["ansi_codes"] = ansi_codes
        parsed_line_info["show_original"] = show_original
        parsed_line_info["original_line"] = line

        return parsed_line_info
    
    def _get_log_level_formatted(self, level: str) -> str:
        if level is not None:
            try:
                return f"[{level.ljust(self.LOGTYPE_WIDTH)}] "
            except:
                return f"[{level}] "
        return ""
    
    def _get_timestamp_formatted(self, timestamp: str) -> str:
        if timestamp is not None:
            # Convert to datetime
            ts = datetime.fromtimestamp(float(timestamp))
            return f"[{ts.strftime('%Y-%m-%d %H:%M:%S')}]"
        return ""
    
    def _get_name_and_pid_formatted(self, name: str, pid: int, color: str) -> str:
        if not name and not pid:
            return ""

        if name:
            try:
                string = f"{name}".ljust(self.NODE_WIDTH)
            except:
                string = f"{name}"
            if pid:
                try:
                    aux_str = f" ({pid})".center(self.PID_WIDTH)
                except:
                    aux_str = f" ({pid})"
                string += aux_str
        elif pid:
            try:
                string = f"{pid}".center(self.PID_WIDTH)
            except:
                string = f"{pid}"

        return self._highlight_block(string, 0, color)

    def _format_log(self, parsed: dict, pid: int) -> str:
        # Extract fields from parsed line
        show_original = parsed['show_original']
        if show_original and not pid:
            return parsed['original_line']
        
        if not pid:
            color = self._get_color_for_pid(randint(0, len(self.BG_COLORS)-1))
        else:
            color = self._get_color_for_pid(pid)

        name_and_pid_formatted = self._get_name_and_pid_formatted(parsed['node_name'], pid, color)
        
        level_formatted = self._get_log_level_formatted(parsed['log_level'])
        timestamp_formatted = self._get_timestamp_formatted(parsed['timestamp'])
        msg = parsed['message']
        ansi_codes = parsed['ansi_codes']
        if ansi_codes:
            # Reconstruct ANSI codes around message
            prefix = ansi_codes[0]
            suffix = ansi_codes[-1] if len(ansi_codes) > 1 else ""
        else:
            prefix = ""
            suffix = ""

        # print(repr(msg))
        # print(self._reduce_consecutive_spaces(msg))

        # First line: full header + first line of message
        line = f"{name_and_pid_formatted} {prefix}{timestamp_formatted}: {level_formatted}{msg}{suffix}"

        return line

    def _reduce_consecutive_spaces(self, text: str) -> str:
        return re.sub(r' +', ' ', text)

    def _highlight_block(self, text:  str, width: int, color: str) -> str:
        try:
            padded = text.ljust(width)
        except:
            padded = text
        return f"{color}{padded}{self.RESET}"

    def _get_color_for_pid(self, pid: int) -> str:
        return self.BG_COLORS[pid % len(self.BG_COLORS)]

    def _on_stdout(self, event: Event):
        pid = event.pid if hasattr(event, 'pid') else None
        text = event.text.decode() if isinstance(event.text, bytes) else event.text

        parsed = self._parse_ros_log_lines(text)
        for line_parsed in parsed:
            if line_parsed:
                output = self._format_log(line_parsed, pid)
            else:
                # Unparsed lines just print raw with minimal formatting
                output = text

            print(output, end='\n')

    def _on_stderr(self, event: Event):
        # Could do same as stdout or mark differently
        self._on_stdout(event)  # For simplicity here

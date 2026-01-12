from launch_ros.actions import Node
import launch
import re
from datetime import datetime
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessIO
from typing import Optional

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
    Formats log messages with color-coded node names, timestamps, and log levels.
    Adds visual clarity to console logs for easier debugging and monitoring.

    Inherits from RegisterEventHandler to handle process IO events.
    
    Args:
        node (Node): The ROS 2 node to attach the logger to.
    Constants:
        BG_COLORS (list): List of ANSI background color codes for node name highlighting.
        RESET (str): ANSI reset code to clear formatting.
        NODE_WIDTH (int): Fixed width for the highlighted node name block.
        DATE_WIDTH (int): Fixed width for the timestamp.
        LOGTYPE_WIDTH (int): Fixed width for the log level.
        LOG_LEVELS (list): List of recognized log levels.
        LOG_LEVEL_RE (re.Pattern): Regex pattern to match log levels in log lines.
        TIMESTAMP_RE (re.Pattern): Regex pattern to match timestamps in log lines.
        NODE_NAME_RE (re.Pattern): Regex pattern to match node names in log lines.
        ANSI_ESCAPE (re.Pattern): Regex pattern to match ANSI escape codes in log lines.
    Methods:
        _on_stdout(event): Handles stdout log events, formats and prints them.
        _on_stderr(event): Handles stderr log events, formats and prints them.
        _parse_ros_log_line(line): Parses a single ROS log line into its components.
        _parse_ros_log_lines(lines): Parses multiple ROS log lines.
        _get_and_remove_log_level(line): Extracts and removes the log level from a log
        _get_and_remove_node_name(line): Extracts and removes the node name from a log line.
        _get_and_remove_timestamp(line): Extracts and removes the timestamp from a log line.
        _remove_match_from_line(line, match): Removes a regex match from a log line.
        _format_log(parsed, pid): Formats the parsed log components into a structured string.
        _highlight_block(text, width, color): Highlights a text block with a background color.
        _get_color_for_pid(pid): Returns a background color based on the process ID.
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

    NODE_WIDTH = 25  # ancho fijo para nodo sombreado
    DATE_WIDTH = 19  # yyyy-mm-dd HH:MM:SS
    LOGTYPE_WIDTH = 5  # ancho fijo para tipo de log

    LOG_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR", "FATAL", "TRACE"]
    LOG_LEVEL_RE = re.compile(r'\[(DEBUG|INFO|WARN|ERROR|FATAL|TRACE)\]', re.IGNORECASE)
    TIMESTAMP_RE = re.compile(r'\[\d{10}\.\d+\]')  # e.g. [1767962265.161910501]
    NODE_NAME_RE = re.compile(r'\[([A-Za-z0-9_.\-\/]+)\]:')
    ANSI_ESCAPE = re.compile(r'(\x1B\[[0-?]*[ -/]*[@-~])')

    # def __init__(self, *args, **kwargs):
    #     kwargs['output'] = 'log'
    #     super().__init__(*args, **kwargs)

    # def get_actions(self):
    #     # Return both Node and its event handler
    #     handler = RegisterEventHandler(
    #         OnProcessIO(
    #             target_action=self,
    #             on_stdout=self._on_stdout,
    #             on_stderr=self._on_stderr,
    #         )
    #     )
    #     return [self, handler]

    def __init__(self, node: Node):
        super().__init__(
            OnProcessIO
            (
                target_action=node,
                on_stdout=self._on_stdout,
                on_stderr=self._on_stderr,
            )
        )
    
    def _parse_ros_log_lines(self, lines: str):
        parsed_lines = []
        for line in lines.splitlines():
            parsed = self._parse_ros_log_line(line)
            parsed_lines.append(parsed)
        return parsed_lines
    
    def _get_and_remove_log_level(self, line: str):
        log_level_match = self.LOG_LEVEL_RE.search(line)
        log_level = None
        if log_level_match:
            log_level = log_level_match.group(1).upper()
            
        # Remove it from line
        line = self._remove_match_from_line(line, log_level_match)
        return log_level, line

    def _get_and_remove_node_name(self, line: str):
        node_name_match = self.NODE_NAME_RE.search(line)
        node_name = None
        if node_name_match:
            node_name = node_name_match.group(1)
        
        # Remove it from line
        line = self._remove_match_from_line(line, node_name_match)
        return node_name, line

    def _get_and_remove_timestamp(self, line: str):
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

    def _remove_match_from_line(self, line: str, match: re.Match):
        if match:
            return line[:match.start()] + line[match.end():]
        return line

    def _parse_ros_log_line(self, line: str):
        original = line
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

        # Remaining line_stripped is the message (strip leading/trailing spaces)
        message = line_stripped.strip()

        return {
            "log_level": log_level,
            "timestamp": timestamp,
            "node_name": node_name,
            "message": message,
            "original_line": original,
            "ansi_codes": ansi_codes,
        }

    def _format_log(self, parsed, pid):
        # Extract fields from parsed line
        name = parsed['node_name'] if parsed['node_name'] else "unknown"
        level = parsed['log_level']
        msg = parsed['message']
        ansi_codes = parsed['ansi_codes']

        if ansi_codes:
            # Reconstruct ANSI codes around message
            prefix = ansi_codes[0]
            suffix = ansi_codes[-1] if len(ansi_codes) > 1 else ''
        else:
            prefix = ''
            suffix = ''

        # Color blocks
        color = self._get_color_for_pid(pid)
        name_to_highlight = f"{name} ({pid})" 
        highlighted_node = self._highlight_block(name_to_highlight, self.NODE_WIDTH, color)
        # highlighted_node = self._highlight_block(name_to_highlight, len(name_to_highlight), color)

        try:
            formatted_level = level.ljust(self.LOGTYPE_WIDTH)
        except:
            formatted_level = level

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # First line: full header + first line of message
        line = [f"{highlighted_node} {prefix}[{formatted_level}] [{timestamp}]: {msg}{suffix}"]

        return "\n".join(line) + "\n"

    def _highlight_block(self, text, width, color):
        try:
            padded = text.ljust(width)
        except:
            padded = text
        return f"{color}{padded}{self.RESET}"

    def _get_color_for_pid(self, pid):
        return self.BG_COLORS[pid % len(self.BG_COLORS)]

    def _on_stdout(self, event):
        pid = event.pid if hasattr(event, 'pid') else 0
        text = event.text.decode() if isinstance(event.text, bytes) else event.text

        parsed = self._parse_ros_log_lines(text)
        for line_parsed in parsed:
            if line_parsed:
                output = self._format_log(line_parsed, pid)
            else:
                # Unparsed lines just print raw with minimal formatting
                output = text

            print(output, end='')

    def _on_stderr(self, event):
        # Could do same as stdout or mark differently
        self._on_stdout(event)  # For simplicity here

# WebSocket Service Configuration - Simplified

"""WebSocket Service Configuration"""

# SSH Connection Settings
SSH_TIMEOUT = 10
# Increase buffer size to improve throughput for large outputs
SSH_BUFFER_SIZE = 4096

# Command Execution Settings
# Timeout before we consider a command "completed" without seeing a prompt
COMMAND_TIMEOUT = 15.0  # seconds
# Polling interval to check for available bytes on the channel
OUTPUT_POLLING_INTERVAL = 0.05  # seconds
# Throttle how often we flush buffered output to the client
OUTPUT_FLUSH_INTERVAL = 0.05  # seconds
# Max chunk size per flush to client
OUTPUT_MAX_CHUNK_SIZE = 16384
# If no output is received for this window while executing a command, mark as completed
QUIET_COMPLETION_WINDOW = 0.8  # seconds

# Output mode
# When True: buffer entire command output and send once upon completion
# When False: stream output chunks as they arrive (throttled)
BATCH_OUTPUT = False

# Pager handling for FortiGate "--More--" prompts
# Options: 'page' (auto send space), 'line' (auto send Enter), 'manual' (frontend decides)
PAGER_MODE = 'page'

# Terminal Settings
TERMINAL_READY_WAIT = 1.0  # seconds for shell readiness

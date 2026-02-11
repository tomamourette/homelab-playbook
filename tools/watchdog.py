import subprocess
import sys
import time
import os
import signal
import select

# Configuration
LOG_STDOUT = "claude_stdout.log"
LOG_STDERR = "claude_debug.log"
TRIPS_LOG = "watchdog_trips.log"

def log_trip(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(TRIPS_LOG, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def run_claude_with_logging(prompt):
    # Construct the command with verbose flags
    cmd = [
        "claude", 
        prompt, 
        "--output-format", "stream-json", 
        "--verbose"
    ]
    
    log_trip(f"Starting Claude with command: {' '.join(cmd)}")
    
    # Open log files
    stdout_f = open(LOG_STDOUT, "a")
    stderr_f = open(LOG_STDERR, "a")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered
    )
    
    log_trip(f"Started process PID: {process.pid}")
    
    try:
        # Monitoring loop
        while True:
            # Check if process is still running
            retcode = process.poll()
            if retcode is not None:
                log_trip(f"Process exited with code {retcode}")
                break
            
            # Use select to read from pipes without blocking
            reads = [process.stdout.fileno(), process.stderr.fileno()]
            ret = select.select(reads, [], [], 1.0)
            
            for fd in ret[0]:
                if fd == process.stdout.fileno():
                    line = process.stdout.readline()
                    if line:
                        stdout_f.write(line)
                        stdout_f.flush()
                elif fd == process.stderr.fileno():
                    line = process.stderr.readline()
                    if line:
                        stderr_f.write(line)
                        stderr_f.flush()
            
            # Heartbeat/Keepalive logic could go here
            
    except KeyboardInterrupt:
        log_trip("Watchdog interrupted by user")
        process.terminate()
    except Exception as e:
        log_trip(f"Watchdog error: {str(e)}")
        process.kill()
    finally:
        stdout_f.close()
        stderr_f.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 watchdog.py <prompt>")
        sys.exit(1)
    
    prompt = sys.argv[1]
    
    # Clean previous logs for fresh run
    open(LOG_STDOUT, 'w').close()
    open(LOG_STDERR, 'w').close()
    
    run_claude_with_logging(prompt)

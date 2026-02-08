#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import signal

def run_with_watchdog(command, timeout_limit=3600):
    """
    Runs a command (like Claude CLI) and monitors it.
    Restarts on failure/kill, or alerts if stuck.
    """
    log_file = "watchdog_trips.log"
    print(f"🚀 Starting Watchdog for: {command}")
    
    while True:
        try:
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            process = subprocess.Popen(
                command, 
                shell=True, 
                stdout=sys.stdout, 
                stderr=sys.stderr,
                preexec_fn=os.setsid
            )
            
            pid = process.pid
            print(f"🛡️  Watchdog active (PID: {pid})")
            
            while True:
                retcode = process.poll()
                if retcode is not None:
                    end_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    if retcode == 0:
                        print("✅ Process finished successfully.")
                        return 0
                    else:
                        reason = f"Exited with code {retcode}"
                        if retcode == -9: reason = "SIGKILL (OOM or External Kill)"
                        elif retcode == -15: reason = "SIGTERM (Termination Request)"
                        
                        log_msg = f"[{end_time}] ⚠️ Trip detected! Reason: {reason} | Command: {command}\n"
                        with open(log_file, "a") as f:
                            f.write(log_msg)
                        
                        print(f"⚠️  {reason}. Restarting in 5s...")
                        time.sleep(5)
                        break
                
                try:
                    os.kill(pid, 0)
                except OSError:
                    end_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    log_msg = f"[{end_time}] 🚨 Process lost! Command: {command}\n"
                    with open(log_file, "a") as f:
                        f.write(log_msg)
                    print("🚨 Process lost! Restarting...")
                    break
                    
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🛑 Watchdog stopped by user.")
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            break
        except Exception as e:
            print(f"❌ Watchdog Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: watchdog.py '<command>'")
        sys.exit(1)
    run_with_watchdog(sys.argv[1])

import subprocess
import signal
import logging

logger = logging.getLogger(__name__)

class CommandException(Exception):
    pass

class CommandTimeout(CommandException):
    def __init__(self, command, timeout):
        self.command = command
        self.timeout = timeout

    def __str__(self):
        return "Command '%s' took longer than %d seconds to execute." % (
                self.command, self.timeout)


class CommandFailure(CommandException):
    def __init__(self, command, return_code, stdout, stderr):
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return "Command '%s' exited with a return code of %d." % (
                self.command, self.return_code,)


def execute(command_string, timeout=None):
    """
    Execute a command with an optional timeout.  If the command takes longer
    than timeout raise a CommandTimeout exception.  If the command fails raise
    a CommandFailure exception.  Otherwise return stdout & stderr from the
    command.
    """
    def handle_sigalrm(signum, frame):
        if signum == signal.SIGALRM:
            logger.error("Command '%s' timed out after %d seconds." % (
                command_string, timeout))
            raise CommandTimeout(command_string, timeout)
    signal.signal(signal.SIGALRM, handle_sigalrm)
    log_header = "Executing command:"
    # If a timeout is given, lets setup an alarm signal
    if timeout:
        log_header += " (timeout: %d)" % (timeout)
        signal.alarm(timeout)
    # Execute the command
    logger.debug(log_header)
    logger.debug("    %s" % (command_string))
    command_object = subprocess.Popen(command_string, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        (stdout, stderr) = command_object.communicate()
    except CommandTimeout, e:
        logger.error("Command timed out, terminating child command.")
        command_object.terminate()
        raise
    if not command_object.returncode == 0:
        signal.alarm(0)
        logger.error("Command '%s' failed with return code %d:" % (
                command_string, command_object.returncode))
        for line in stdout.split('\n'):
            logger.error("    stdout: %s" % (line))
        for line in stderr.split('\n'):
            logger.error("    stderr: %s" % (line))
        raise CommandFailure(command_string, command_object.returncode,
                stdout, stderr)
    signal.alarm(0)
    return (stdout, stderr)
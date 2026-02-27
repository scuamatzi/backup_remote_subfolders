import stat
# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------

# def find_private_key(key_dir):
#    """
#    Find a private key file in the given directory.
#    Returns the full path to the first file that does not end with '.pub'.
#    If none found, returns None.
#    """
#    if not os.path.isdir(key_dir):
#        return None
#    for fname in os.listdir(key_dir):
#        full_path = os.path.join(key_dir, fname)
#        if os.path.isfile(full_path) and not fname.endswith('.pub'):
#            return full_path
#    return None


def is_directory(sftp, path):
    """
    Check if the given path on the remote server is a directory.
    """
    try:
        attrs = sftp.stat(path)
        return stat.S_ISDIR(attrs.st_mode)
    except IOError:
        return False


def create_remote_zip(ssh_client, remote_dir, subfolder):
    """
    Create a zip archive of a subfolder inside remote_dir.
    The archive is created inside remote_dir with name subfolder.zip.
    Returns True if successful, False otherwise.
    """

    # Command: change to remote_dir and zip the subfolder quietly, recursively
    command = f"cd {remote_dir} && zip -rq {subfolder}.zip {subfolder}"
    stdin, stdout, stderr = ssh_client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        error = stderr.read().decode().strip()
        print(f"Error creating zip folder for {subfolder}: {error}")
        return False

    return True

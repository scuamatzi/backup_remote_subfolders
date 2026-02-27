import getpass
import os
import paramiko
import sys
import stat
from scp import SCPClient  # optional, but we'll use SFTP directly

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

LOCAL_DIR = "emails"  # Local folder to store downloaded zips
# KEY_DIR = os.path.expanduser("~/.ssh/keys")  # Directory containing SSH keys
DEFAULT_PORT = 22

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


# ----------------------------------------------------------------------
# Main script
# ----------------------------------------------------------------------


def main():
    print("=== Remote folder zipper and downloader ===\n")

    # Gather connection details
    host = input("Server URL: ").strip()
    if not host:
        print("Host is required.")
        sys.exit(1)

    port_input = input(f"Port (default {DEFAULT_PORT}): ").strip()
    port = int(port_input) if port_input else DEFAULT_PORT

    username = input("SSH Username: ").strip()
    if not username:
        print("Username is required.")
        sys.exit(1)

    remote_dir = input(
        "Remote directory to process (e.g., /home/server1/emails/): "
    ).strip()
    if not remote_dir:
        print("Remote directory is required.")
        sys.exit(1)

    # Find SSH private key
    # key_path = find_private_key(KEY_DIR)
    # if not key_path:
    #    print(f"No private key found in {KEY_DIR}. Exiting.")
    #    sys.exit(1)
    # print(f"Using SSH key: {key_path}")

    # Prepare local directory
    local_dir_full = os.path.join(os.getcwd(), LOCAL_DIR)
    os.makedirs(local_dir_full, exist_ok=True)
    print(f"Local download folder: {local_dir_full}")

    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"Connecting to {host}:{port} as {username}...")
        ssh.connect(hostname=host, port=port, username=username)
        print("Connected!")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    # Open SFTP session
    sftp = ssh.open_sftp()

    try:
        #  List items in remote directory
        print(f"Listing contents of {remote_dir}...")
        items = sftp.listdir(remote_dir)
        subfolders = []

        for item in items:
            full_path = os.path.join(remote_dir, item).replace(
                "\\", "/"
            )  # ensure posix path
            if is_directory(sftp, full_path):
                subfolders.append(item)

        if not subfolders:
            print("No subfolders found. Exiting.")
            sys.exit(1)

        print(f"Found {len(subfolders)} subfolder(s): {', '.join(subfolders)}")

        # Process each subfolder
        for sub in subfolders:
            print(f"\nProcessing '{sub}' ...")

            # Create zip on remote server
            if not create_remote_zip(ssh, remote_dir, sub):
                print(f"Skipping download for '{sub}' due to zip error.")
                continue

            remote_zip_path = os.path.join(remote_dir, f"{sub}.zip").replace(
                "\\", "/   "
            )  # ensure posix path

            local_zip_path = os.path.join(local_dir_full, f"{sub}.zip")

            # Download the zip file
            try:
                print(f"Downloading {sub}.zip ...")
                sftp.get(remote_zip_path, local_zip_path)
                print(f"Downloaded to {local_zip_path}")
            except Exception as e:
                print(f"Download of '{sub}.zip' failed: {e}")
                continue

            # Optional: remove remote zip after successful download
            # Uncomment the next two lines if you want to clean up
            # sftp.remove(remote_zip_path)
            # print(f"Removed remote {sub}.zip")

        print("\nAll done.")
    except Exception as e:
        print(f"An error ocurred processing subfolders on remote server:: {e}")
    finally:
        sftp.close()
        ssh.close()
        print("Connection Closed!")


if __name__ == "__main__":
    main()

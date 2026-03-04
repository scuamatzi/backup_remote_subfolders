import getpass
from modules.ssh_tools import is_directory, create_remote_zip, remote_zip_file_exist
import os
import paramiko
import sys
# import stat
# from scp import SCPClient  # optional, but we'll use SFTP directly

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

LOCAL_DIR = "backups"  # Local folder to store downloaded zips
# KEY_DIR = os.path.expanduser("~/.ssh/keys")  # Directory containing SSH keys
DEFAULT_PORT = 22


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

    use_password = input("Need password for ssh connection? (y/n) :  ").strip()

    if use_password in ["y", "yes"]:
        passwd = getpass.getpass("Enter ssh password: ")
    else:
        print("\n")
        print("*" * 60)
        print("To work without password:")
        print("- Remember to create ssh key with 'ssh-keygen' command.")
        print("- Copy ssh key to remote server with 'ssh-copy-id' command.")
        print("*" * 60)
        nopass_answer = input("\nReady to continue without password? (y/n): ").strip()

        if nopass_answer in ["no", "n"]:
            print("\nExiting!")
            sys.exit(0)

        if nopass_answer not in ["y", "yes"]:
            print("\nBad answer. Exiting...")
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
        if use_password in ["y", "yes"]:
            ssh.connect(hostname=host, port=port, username=username, password=passwd)
        else:
            ssh.connect(hostname=host, port=port, username=username)
        print("Connected!")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    # Open SFTP session
    sftp = ssh.open_sftp()

    try:
        #  List items in remote directory
        print(f"\nListing contents of {remote_dir}...")
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

        total_subfolders = len(subfolders)
        print(f"Found {total_subfolders} subfolder(s): {', '.join(subfolders)}")

        # Process each subfolder
        for idx, sub in enumerate(subfolders, 1):
            print(f"\nProcessing '{sub}' ({idx}/{total_subfolders}) ...")

            local_zip_path = os.path.join(local_dir_full, f"{sub}.zip")

            remote_zip_path = os.path.join(remote_dir, f"{sub}.zip").replace(
                "\\", "/   "
            )  # ensure posix path

            # Check if zip file exists, then skip
            if os.path.exists(local_zip_path):
                print(f"\nFile '{sub}.zip' already downloaded. Skipping")
                continue

            # Check if remote zip file does not exists
            if not remote_zip_file_exist(sftp, remote_zip_path):
                # Create zip on remote server
                if not create_remote_zip(ssh, remote_dir, sub):
                    print(f"Skipping download for '{sub}' due to zip error.")
                    continue

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

from rich.console import Console
from rich.panel import Panel
import getpass
from modules.ssh_tools import (
    is_directory,
    create_remote_zip,
    remote_zip_file_exist,
    get_host,
    get_port,
    get_username,
    get_remote_dir,
)
import os
import paramiko
import sys

console = Console()
# import stat
# from scp import SCPClient  # optional, but we'll use SFTP directly


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
LOCAL_DIR = "backups"  # Local folder to store downloaded zips
# KEY_DIR = os.path.expanduser("~/.ssh/keys")  # Directory containing SSH keys
DEFAULT_PORT = 22


# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------
def confirm_keygen_usage():
    # print("\n")
    # print("*" * 60)
    # print("To work without password:")
    # print("- Remember to create ssh key with 'ssh-keygen' command.")
    # print("- Copy ssh key to remote server with 'ssh-copy-id' command.")
    # print("*" * 60)
    console.print(
        Panel(
            "To work without password:\n"
            + "- Remember to create ssh key with 'ssh-keygen' command.\n"
            + "- Copy ssh key to remote server with 'ssh-copy-id' command.",
            title="Warning!!",
        )
    )
    nopass_answer = input("\nReady to continue without password? (y/n): ").strip()

    if nopass_answer in ["no", "n"]:
        print("\nExiting!")
        sys.exit(0)

    if nopass_answer not in ["y", "yes"]:
        print("\nBad answer. Exiting...")
        sys.exit(1)
    return


# ----------------------------------------------------------------------
# Main script
# ----------------------------------------------------------------------
def main():
    # print("=== Remote folder zipper and downloader ===\n")
    console.print(Panel("   Remote folder zipper and downloader"))

    # Gather connection details
    host = get_host()

    port = get_port(DEFAULT_PORT)

    username = get_username()

    remote_dir = get_remote_dir()

    use_password = input("Need password for ssh connection? (y/n) :  ").strip()

    if use_password in ["y", "yes"]:
        passwd = getpass.getpass("Enter ssh password: ")
    else:
        confirm_keygen_usage()

    # Find SSH private key
    # key_path = find_private_key(KEY_DIR)
    # if not key_path:
    #    print(f"No private key found in {KEY_DIR}. Exiting.")
    #    sys.exit(1)
    # print(f"Using SSH key: {key_path}")

    # Prepare local directory
    local_dir_full = os.path.join(os.getcwd(), LOCAL_DIR)
    os.makedirs(local_dir_full, exist_ok=True)
    print(f"\nLocal download folder: {local_dir_full}")

    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        print(f"\nConnecting to {host}:{port} as {username}...")
        if use_password in ["y", "yes"]:
            with console.status(""):
                ssh.connect(
                    hostname=host, port=port, username=username, password=passwd
                )
        else:
            with console.status(""):
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
        with console.status(""):
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
            with console.status(""):
                print(f"\nProcessing '{sub}' ({idx}/{total_subfolders}) ...")

                local_zip_path = os.path.join(local_dir_full, f"{sub}.zip")

                remote_zip_path = os.path.join(remote_dir, f"{sub}.zip").replace(
                    "\\", "/   "
                )  # ensure posix path

                # Check if zip file exists, then skip
                if os.path.exists(local_zip_path):
                    print(f"File '{sub}.zip' already downloaded. Skipping")
                    continue

                # Check if remote zip file does not exists
                if not remote_zip_file_exist(sftp, remote_zip_path):
                    # Create zip on remote server
                    if not create_remote_zip(ssh, remote_dir, sub):
                        print(f"Skipping download for '{sub}' due to zip error.")
                        continue

            # Download the zip file
            try:
                with console.status(""):
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

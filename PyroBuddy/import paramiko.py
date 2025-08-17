import paramiko
import time

# -----------------------------
# CONFIGURATION (You can change these)
# -----------------------------
HOST = "45.76.31.253"
USERNAME = "root"
PASSWORD = "5Ee#ExyMAP}uXG2a"
POSTAL_YML_PATH = "/opt/postal/config/postal.yml"
SECRET_KEY = "2049f7bdc9af00730e693042028edc67d7baf947d32f05f46f7d7e2b6fa197a7cb65f70674cbd1f607731eb51ebd00bf8d9cc0dcbac18e"

# -----------------------------
# FUNCTION TO CONNECT AND EXECUTE
# -----------------------------
def execute_ssh_commands():
    try:
        print("[+] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USERNAME, password=PASSWORD)

        # Backup original postal.yml
        print("[+] Backing up postal.yml...")
        ssh.exec_command(f"cp {POSTAL_YML_PATH} {POSTAL_YML_PATH}.bak")

        # Fix postal.yml content
        fixed_yml = f"""
version: 2

web:
  host: 0.0.0.0
  port: 5000
  secret_key: '{SECRET_KEY}'

smtp:
  port: 2525

main_db:
  adapter: mysql2
  host: mariadb
  database: postal
  username: postal
  password: qwe123qwe

rabbitmq:
  host: rabbitmq
  port: 5672
  username: postal
  password: qwe123qwe
  vhost: postal
"""
        print("[+] Updating postal.yml...")
        sftp = ssh.open_sftp()
        with sftp.file(POSTAL_YML_PATH, 'w') as f:
            f.write(fixed_yml)
        sftp.close()

        # Restart Postal
        print("[+] Restarting Postal Docker containers...")
        ssh.exec_command("cd /opt/postal && docker compose down && docker compose up -d")
        time.sleep(5)

        # Check logs
        print("[+] Fetching postal-web logs...")
        stdin, stdout, stderr = ssh.exec_command("docker logs postal-web | tail -n 100")
        logs = stdout.read().decode()
        print("----- postal-web Logs -----")
        print(logs)

        # Test port 5000
        print("[+] Testing localhost:5000 availability...")
        stdin, stdout, stderr = ssh.exec_command("curl -I http://127.0.0.1:5000/")
        result = stdout.read().decode()
        print("----- curl Output -----")
        print(result)

        ssh.close()
        print("[✓] Done. Postal should now be accessible if DNS is correctly configured.")

    except Exception as e:
        print(f"[!] Error: {e}")


# Run the function
downloads = execute_ssh_commands()
{{- define "qemu.runtime.catalog-arm64.json" -}}
{
  "ubuntu2404": {
    "title": "Ubuntu 24.04 LTS",
    "user": "ubuntu",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/noble-server-cloudimg-arm64.img",
    "sums": "https://cdn.olares.com/linux/ubuntu2404-arm64-SHA256SUMS",
    "algorithm": "sha256",
    "digest": "1d6bffe64b848468ac97f821d369a4846d983de1800ccf6b5ec8853e85cefc55"
  },
  "ubuntu2604": {
    "title": "Ubuntu 26.04 LTS",
    "user": "ubuntu",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/ubuntu-26.04-server-cloudimg-arm64.img",
    "sums": "https://cdn.olares.com/linux/ubuntu2604-arm64-SHA256SUMS",
    "algorithm": "sha256",
    "digest": "63a93bd5a8d76e33b15ceb5daa3657bd79be804748051ab178e643b0f5da22e7"
  },
  "debian12": {
    "title": "Debian 12",
    "user": "debian",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/debian-12-genericcloud-arm64.qcow2",
    "sums": "https://cdn.olares.com/linux/debian12-arm64-SHA512SUMS",
    "algorithm": "sha512",
    "digest": "835b929522716de9798d1c0fbe61caae8313ab78858b278f3389a2db922ae42e4619b4a776ecad39583c149fb85334a2f8cdae685bc56987160e5c86a2354375"
  },
  "debian13": {
    "title": "Debian 13",
    "user": "debian",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/debian-13-genericcloud-arm64.qcow2",
    "sums": "https://cdn.olares.com/linux/debian13-arm64-SHA512SUMS",
    "algorithm": "sha512",
    "digest": "d8470b8c6c38fead046c794b5800a5a7b96672d5bcf543cc230ceb0c4b8ace05ed341a0c8928045422243fde26b2f1f2f58e99244c65709ffda2e3d4b674dd5a"
  },
  "rocky9": {
    "title": "Rocky Linux 9",
    "user": "rocky",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Rocky-9-GenericCloud-Base-9.8-20260525.0.aarch64.qcow2",
    "algorithm": "sha256",
    "digest": "24692a444f1f0b8bb95375c38c8b43f8099a115347623691be2c330b40c8a1fe",
    "sums": "https://cdn.olares.com/linux/Rocky-9-GenericCloud-Base-9.8-20260525.0.aarch64.qcow2.CHECKSUM"
  },
  "rocky10": {
    "title": "Rocky Linux 10",
    "user": "rocky",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Rocky-10-GenericCloud-Base-10.2-20260525.0.aarch64.qcow2",
    "algorithm": "sha256",
    "digest": "457c8375e19496f43a25c4a6169fa11237536c53cef6f85a20ea3c5a751aa0f5",
    "sums": "https://cdn.olares.com/linux/Rocky-10-GenericCloud-Base-10.2-20260525.0.aarch64.qcow2.CHECKSUM"
  },
  "fedora43": {
    "title": "Fedora 43",
    "user": "fedora",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Fedora-Cloud-Base-Generic-43-1.6.aarch64.qcow2",
    "algorithm": "sha256",
    "digest": "66031aea9ec61e6d0d5bba12b9454e80ca94e8a79c913d37ded4c60311705b8b",
    "sums": "https://cdn.olares.com/linux/Fedora-Cloud-43-1.6-aarch64-CHECKSUM"
  },
  "fedora44": {
    "title": "Fedora 44",
    "user": "fedora",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Fedora-Cloud-Base-Generic-44-1.7.aarch64.qcow2",
    "algorithm": "sha256",
    "digest": "55c60a3b80d3616a08705afd0459e75fe9f03c54aba7a46e4002a41a72fa0d5b",
    "sums": "https://cdn.olares.com/linux/Fedora-Cloud-44-1.7-aarch64-CHECKSUM"
  }
}
{{- end -}}

{{- define "qemu.runtime.catalog.json" -}}
{
  "ubuntu2404": {
    "title": "Ubuntu 24.04 LTS",
    "user": "ubuntu",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/noble-server-cloudimg-amd64.img",
    "sums": "https://cdn.olares.com/linux/ubuntu2404-SHA256SUMS",
    "algorithm": "sha256",
    "digest": "6a81c37564db9b1ee84e141922625e1d7c5b389b99bb3c572e0243607d5bb4d2"
  },
  "ubuntu2604": {
    "title": "Ubuntu 26.04 LTS",
    "user": "ubuntu",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/ubuntu-26.04-server-cloudimg-amd64.img",
    "sums": "https://cdn.olares.com/linux/ubuntu2604-SHA256SUMS",
    "algorithm": "sha256",
    "digest": "8800651811af9a85465ad1d552add729947bb16488dddb4a9b5305a3d97332b2"
  },
  "debian12": {
    "title": "Debian 12",
    "user": "debian",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/debian-12-genericcloud-amd64.qcow2",
    "sums": "https://cdn.olares.com/linux/debian12-SHA512SUMS",
    "algorithm": "sha512",
    "digest": "a09170d17e13af43da61774666f520e3bbec0f8bd96b4db37c15f3426fb327ccad950b80dbe78c09aa5ca90ce5015e99334b0ba5188fd4018736bc3fb5f0882c"
  },
  "debian13": {
    "title": "Debian 13",
    "user": "debian",
    "group": "sudo",
    "url": "https://cdn.olares.com/linux/debian-13-genericcloud-amd64.qcow2",
    "sums": "https://cdn.olares.com/linux/debian13-SHA512SUMS",
    "algorithm": "sha512",
    "digest": "f46f0671a6e5bdec5291ab8972bae2f10e5408c2f64a74078f11efc2f06a436a9d0313ed50e0472542eeabf780e9f7c792ac0a314c6c20507fcd9fd81b468c3d"
  },
  "rocky9": {
    "title": "Rocky Linux 9",
    "user": "rocky",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Rocky-9-GenericCloud-Base-9.8-20260525.0.x86_64.qcow2",
    "algorithm": "sha256",
    "digest": "92c206cc6f790c61583247eefe87890f8828420662c17cacf247cec78ab4eec8"
  },
  "rocky10": {
    "title": "Rocky Linux 10",
    "user": "rocky",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Rocky-10-GenericCloud-Base-10.2-20260525.0.x86_64.qcow2",
    "algorithm": "sha256",
    "digest": "9fc9e9ff16888bb68ac39b0392e25c9c92684d50c85f1cce6ab549363bbc4b48"
  },
  "fedora43": {
    "title": "Fedora 43",
    "user": "fedora",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2",
    "algorithm": "sha256",
    "digest": "846574c8a97cd2d8dc1f231062d73107cc85cbbbda56335e264a46e3a6c8ab2f"
  },
  "fedora44": {
    "title": "Fedora 44",
    "user": "fedora",
    "group": "wheel",
    "url": "https://cdn.olares.com/linux/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
    "algorithm": "sha256",
    "digest": "28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"
  }
}
{{- end -}}

{{- define "qemu.runtime.engine.py" -}}
"""Non-root QEMU supervisor with setup progress and guest filesystem expansion."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import shlex
import sys
import socket
import subprocess
import threading
import time
import vm_platform

ROOT, STORE, TMP = Path('/opt/olares'), Path('/storage'), Path('/tmp')
GIB = 1024 ** 3
stop = threading.Event()
state = {'phase': 'preparing', 'message': 'Checking virtual machine settings.',
         'message_zh': '正在检查虚拟机设置。', 'ready': False, 'connectable': False,
         'percent': None, 'warning': ''}
web = vm = transfer = None
guest_username = "ubuntu"


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)


def publish(phase=None, en=None, zh=None, **values):
    state.update(values)
    if phase:
        state['phase'] = phase
    if en:
        state['message'], state['message_zh'] = en, zh or en
    state['updated'] = int(time.time())
    write_json(TMP / 'status.json', state)
    if phase:
        print(f"{phase}: {state['message']}", flush=True)


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs).stdout


def integer(name, default, minimum, maximum):
    text = os.environ.get(name, str(default))
    if not re.fullmatch(r'[0-9]+', text) or not minimum <= int(text) <= maximum:
        raise ValueError(f'{name} must be {minimum}–{maximum}.')
    return int(text)


def download(entry):
    global transfer
    part, source = STORE / 'server.qcow2.part', STORE / 'download-source.json'
    previous_source = json.loads(source.read_text()) if source.exists() else {}
    if previous_source.get('url') != entry['url']:
        part.unlink(missing_ok=True)
    write_json(source, {'url': entry['url']})
    expected = entry.get('digest')
    if not expected:
        raw = run(['curl', '-4', '-fsSL', '--connect-timeout', '20', '--max-time', '120',
                   '--retry', '3', entry['sums']], timeout=500)
        name = entry['url'].rsplit('/', 1)[1]
        for line in raw.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[1].lstrip('*') == name:
                expected = fields[0]
                break
    length = 64 if entry['algorithm'] == 'sha256' else 128
    if not expected or not re.fullmatch('[0-9a-f]{' + str(length) + '}', expected):
        raise ValueError('Official checksum not found for the selected image.')
    headers = TMP / 'download.headers'
    headers.unlink(missing_ok=True)
    publish('downloading', 'Downloading the system image from CDN. Interrupted downloads resume automatically.',
            '正在从 CDN 下载系统镜像，中断后可在重启时继续下载。', downloaded=part.stat().st_size if part.exists() else 0)
    with (TMP / 'download.log').open('w') as log:
        transfer = subprocess.Popen(['curl', '-4', '-fL', '--connect-timeout', '20',
            '--max-time', '3600', '--retry', '8', '--retry-all-errors',
            '--retry-delay', '3', '--continue-at', '-',
            '--dump-header', str(headers), '-o', str(part), entry['url']],
            stdout=subprocess.DEVNULL, stderr=log)
        previous = part.stat().st_size if part.exists() else 0
        while transfer.poll() is None:
            if stop.wait(1):
                transfer.terminate()
                raise InterruptedError()
            current = part.stat().st_size if part.exists() else 0
            total = 0
            if headers.exists():
                raw = headers.read_text(errors='replace')
                ranges = re.findall(r'(?im)^content-range:.*?/(\d+)\s*$', raw)
                lengths = re.findall(r'(?im)^content-length:\s*(\d+)\s*$', raw)
                total = int(ranges[-1]) if ranges else int(lengths[-1]) if lengths else 0
            publish(downloaded=current, total=total, speed=max(0, current - previous),
                    percent=min(100, current * 100 / total) if total else None)
            previous = current
        if transfer.returncode:
            print(f'Image download failed after retries (curl exit {transfer.returncode}). See /tmp/download.log.', flush=True)
            raise RuntimeError('Image download failed. Restart the app to retry; downloaded data is retained.')
    publish('verifying', 'Verifying the image checksum.', '正在校验镜像完整性。', speed=0, percent=None)
    digest = hashlib.new(entry['algorithm'])
    with part.open('rb') as file:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        part.unlink()
        raise RuntimeError('Image checksum mismatch. The incomplete image was removed; restart to download again.')
    return part


def agent(command, arguments=None, timeout=3):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(timeout)
        connection.connect('/tmp/qga.sock')
        reader = connection.makefile('rb')
        sync_id = int(time.time() * 1000)
        requests = [{'execute': 'guest-sync-delimited', 'arguments': {'id': sync_id}},
                    {'execute': command, **({'arguments': arguments} if arguments else {})}]
        for index, payload in enumerate(requests):
            connection.sendall(json.dumps(payload).encode() + b'\n')
            while True:
                line = reader.readline()
                if not line:
                    raise RuntimeError('Guest agent disconnected.')
                try:
                    response = json.loads(line.lstrip(b'\xff'))
                except ValueError:
                    continue
                if 'error' in response:
                    raise RuntimeError(response['error'].get('desc', 'Guest agent error'))
                if 'return' in response:
                    if index == 0 and response['return'] != sync_id:
                        continue
                    break
        return response['return']


def guest_exec(script, timeout=240):
    askpass = TMP / 'ssh-askpass'
    askpass.write_text('#!' + sys.executable + '\nimport os\nprint(os.environ["VM_PASSWORD"])\n')
    askpass.chmod(0o700)
    env = dict(os.environ, SSH_ASKPASS=str(askpass), SSH_ASKPASS_REQUIRE='force', DISPLAY='olares:0')
    argv = ['ssh', '-p', '2222', '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
            '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile=/storage/ssh_known_hosts',
            '-o', 'PreferredAuthentications=password', '-o', 'PubkeyAuthentication=no',
            '-o', 'NumberOfPasswordPrompts=1', guest_username + '@127.0.0.1',
            'sudo -n /bin/sh -c ' + shlex.quote(script)]
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, env=env, text=True,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError('Guest maintenance timed out. Check the system console.') from None
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Guest operation failed.')[-700:])
    return result.stdout


GROW_ROOT = r'''set -eu
source=$(findmnt -n -o SOURCE /)
root=$(readlink -f "${source%%\[*}")
parent=$(lsblk -n -o PKNAME "$root" | head -n 1)
partition_file="/sys/class/block/$(basename "$root")/partition"
part=''
if [ -r "$partition_file" ]; then part=$(cat "$partition_file"); fi
if [ -z "$parent" ] || [ -z "$part" ]; then
  echo 'Automatic expansion requires a root filesystem on a plain disk partition.' >&2; exit 1
fi
set +e
result=$(growpart "/dev/$parent" "$part" 2>&1); code=$?
set -e
if [ "$code" -ne 0 ]; then
  case "$result" in *NOCHANGE*) ;; *) echo "$result" >&2; exit 1;; esac
fi
case "$(findmnt -n -o FSTYPE /)" in
  ext4|ext3|ext2) resize2fs "$root" ;;
  xfs) xfs_growfs / ;;
  btrfs) btrfs filesystem resize max / ;;
  *) echo 'Filesystem requires manual expansion.' >&2; exit 1 ;;
esac
df -B1 /
'''

WAIT_INIT = '''cloud-init status --wait
code=$?
if [ "$code" -eq 2 ]; then echo OLARES_CLOUD_INIT_WARNING; exit 0; fi
exit "$code"
'''


def prepare_seed(entry):
    seed = TMP / 'seed'
    seed.mkdir(exist_ok=True)
    packages = ['qemu-guest-agent', 'cloud-guest-utils' if entry['group'] == 'sudo' else 'cloud-utils-growpart']
    config = {'users': [{'name': entry['user'], 'groups': [entry['group']], 'shell': '/bin/bash',
                'sudo': 'ALL=(ALL) NOPASSWD:ALL', 'lock_passwd': False,
                'plain_text_passwd': os.environ['VM_PASSWORD']}],
              'ssh_pwauth': True, 'chpasswd': {'expire': False},
              'apt': {'conf': 'Acquire::Retries "3";\nAcquire::IndexTargets::deb::CNF::DefaultEnabled "false";\n'},
              'packages': packages, 'runcmd': [['systemctl', 'start', 'qemu-guest-agent']]}
    if entry['user'] == 'fedora':
        config['preserve_hostname'] = True
    (seed / 'user-data').write_text('#cloud-config\n' + json.dumps(config))
    (seed / 'meta-data').write_text('instance-id: olares-qemu-server-v1\nlocal-hostname: linux-server\n')
    run(['genisoimage', '-quiet', '-output', '/tmp/seed.iso', '-volid', 'cidata',
         '-joliet', '-rock', str(seed / 'user-data'), str(seed / 'meta-data')])
    write_json(TMP / 'connection.json', {'username': entry['user'], 'password': os.environ['VM_PASSWORD']})


def configure_and_start():
    global vm, guest_username
    cpu = integer('CPU_CORES', 2, 1, 8)
    memory = integer('MEMORY_GB', 2, 1, 32)
    disk = integer('DISK_SIZE_GB', 32, 16, 512)
    distribution = os.environ.get('DISTRIBUTION', 'ubuntu2404')
    arch = vm_platform.architecture()
    catalog_file = 'catalog-arm64.json' if arch == 'arm64' else 'catalog.json'
    catalog = json.loads((ROOT / catalog_file).read_text())
    if distribution not in catalog:
        raise ValueError('Unsupported distribution/version selection.')
    entry = dict(catalog[distribution])
    guest_username = entry['user']
    cdn = os.environ.get('CDN_HOST', 'https://cdn.olares.com').rstrip('/')
    for field in ('url', 'sums'):
        if field in entry:
            entry[field] = cdn + '/linux/' + entry[field].rsplit('/', 1)[-1]
    publish(title=entry['title'], cpu=cpu, memory=memory, disk=disk, architecture=arch)
    fd = os.open('/dev/kvm', os.O_RDWR)
    try:
        if fcntl.ioctl(fd, 0xAE00, 0) != 12:
            raise RuntimeError('Unsupported KVM API.')
    finally:
        os.close(fd)
    image, marker = STORE / 'server.qcow2', STORE / 'distribution'
    arch_marker = STORE / 'architecture'
    vm_platform.check_disk_architecture(arch, image, arch_marker)
    if image.exists() and not marker.exists():
        marker.write_text('ubuntu2404\n')
    if marker.exists() and marker.read_text().strip() != distribution:
        raise RuntimeError('The selected version does not match the existing disk. Restore the original selection or create a new disk.')
    if not image.exists():
        if not 8 <= len(os.environ.get('VM_PASSWORD', '')) <= 128:
            raise ValueError('Set an initial password of 8–128 characters when installing a new VM.')
        part = download(entry)
        publish('disk', 'Creating the persistent system disk.', '正在创建持久化系统盘。', percent=None)
        original = json.loads(run(['qemu-img', 'info', '--output=json', str(part)]))['virtual-size']
        if disk * GIB < original:
            raise ValueError('Selected disk size is smaller than the official image minimum.')
        run(['qemu-img', 'resize', str(part), str(disk * GIB)])
        marker.write_text(distribution + '\n')
        arch_marker.write_text(arch + chr(10))
        part.replace(image)
    current = json.loads(run(['qemu-img', 'info', '--output=json', str(image)]))['virtual-size']
    if disk * GIB > current:
        publish('disk', 'Saving a disk backup before expansion.', '正在保存扩容前的磁盘备份。', percent=None)
        backup = STORE / 'before-expansion.qcow2.tmp'
        run(['qemu-img', 'convert', '-O', 'qcow2', str(image), str(backup)])
        backup.replace(STORE / 'before-expansion.qcow2')
        if stop.is_set():
            raise InterruptedError()
        publish('disk', 'Expanding the virtual disk. Existing data is retained.', '正在扩大虚拟磁盘，保留已有数据。', percent=None)
        run(['qemu-img', 'resize', str(image), str(disk * GIB)])
        current = disk * GIB
    elif disk * GIB < current:
        publish(warning=f'Disk shrink is not supported. The existing {current // GIB} GiB disk is retained. Set DISK_SIZE_GB to {current // GIB} or larger.')
    publish(disk=current // GIB)
    vm_platform.prepare_firmware(arch, STORE)
    prepare_seed(entry)
    publish('booting', 'Starting the virtual machine with KVM acceleration.', '正在使用 KVM 加速启动虚拟机。', percent=None)
    vm = subprocess.Popen(vm_platform.command(arch, cpu, memory, image, STORE))
    publish('initializing', 'Waiting for SSH and cloud-init. The console is available during setup.',
            '正在等待 SSH 和系统初始化，期间可以打开控制台。', connectable=True)
    end = time.monotonic() + 900
    while time.monotonic() < end and not stop.wait(3):
        if vm.poll() is not None:
            raise RuntimeError('The virtual machine stopped during startup. Check container logs and the console.')
        try:
            guest_exec('true', timeout=15)
            break
        except (OSError, RuntimeError, ValueError, TimeoutError):
            pass
    else:
        raise TimeoutError('SSH is not ready. Open the console and check the login service; the virtual disk is retained.')
    init_output = guest_exec(WAIT_INIT, timeout=600)
    if 'OLARES_CLOUD_INIT_WARNING' in init_output:
        publish(warning='Cloud-init completed with recoverable warnings. Run cloud-init status --long for details.')
    publish('expanding', 'Checking the root partition and filesystem capacity.', '正在检查并扩展系统分区与文件系统。')
    try:
        output = guest_exec(GROW_ROOT)
        print('Guest filesystem check:\n' + output, flush=True)
    except (RuntimeError, TimeoutError) as error:
        publish(warning=state.get('warning', '') + '\nAutomatic filesystem expansion needs attention: ' + str(error))
    publish('ready', 'The server is ready. CPU and memory edits restart the VM; disk size can only grow.',
            '服务器已就绪。修改 CPU 和内存后会重启，磁盘仅支持扩容。', ready=True, percent=100)
    while not stop.wait(2):
        if vm.poll() is not None:
            publish('stopped', 'The guest has shut down. Restart the app to start it again.', '虚拟机已关机，重启应用可再次启动。', ready=False)
            stop.wait()
            break


def shutdown():
    if transfer is not None and transfer.poll() is None:
        transfer.terminate()
    if vm is not None and vm.poll() is None:
        try:
            with socket.socket(socket.AF_UNIX) as connection:
                connection.settimeout(2)
                connection.connect('/tmp/qemu-monitor.sock')
                connection.sendall(b'system_powerdown\n')
            vm.wait(timeout=105)
        except (OSError, subprocess.TimeoutExpired):
            vm.terminate()
            try:
                vm.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vm.kill()
    if web is not None and web.poll() is None:
        web.terminate()


def main():
    global web
    os.umask(0o077)
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    shutil.copyfile(ROOT / 'index.html', TMP / 'index.html')
    publish()
    web = subprocess.Popen(['nginx', '-c', str(ROOT / 'nginx.conf'), '-g', 'daemon off;'])
    try:
        configure_and_start()
    except InterruptedError:
        pass
    except Exception as error:
        publish('failed', str(error), ready=False, percent=None)
        while not stop.wait(2):
            if web.poll() is not None:
                break
    finally:
        shutdown()


if __name__ == '__main__':
    main()
{{- end -}}

{{- define "qemu.runtime.frontend.conf" -}}
pid /tmp/nginx.pid;
error_log /dev/stderr;
events { worker_connections 128; }
http {
  access_log off;
  client_body_temp_path /tmp/client;
  proxy_temp_path /tmp/proxy;
  fastcgi_temp_path /tmp/fastcgi;
  uwsgi_temp_path /tmp/uwsgi;
  scgi_temp_path /tmp/scgi;
  map $http_upgrade $connection_upgrade { default upgrade; '' close; }
  server {
    listen 8006;
    location / {
      proxy_pass http://qemu:8006;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection $connection_upgrade;
      proxy_read_timeout 3600s;
      proxy_buffering off;
    }
  }
}
{{- end -}}

{{- define "qemu.runtime.index.html" -}}
<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QEMU Server</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#20332f;background:#f4f6f5;font-synthesis:none}*{box-sizing:border-box}body{margin:0}main{max-width:780px;margin:0 auto;padding:28px 24px}.brand{font-size:11px;letter-spacing:2px;color:#6e817a;font-weight:650}header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:15px 0 20px}h1{font-size:27px;letter-spacing:-.7px;margin:0 0 7px}.resource-row{display:flex;align-items:center;gap:8px;font-size:12px;color:#6c7d76}.help{position:relative;display:inline-flex}.help summary{cursor:pointer;list-style:none;width:17px;height:17px;border:1px solid #9baca3;border-radius:50%;display:grid;place-items:center;font-size:11px}.help summary::-webkit-details-marker{display:none}.help p{position:absolute;z-index:3;top:17px;right:-12px;width:280px;padding:13px 15px;background:#253e33;color:#fff;box-shadow:0 6px 20px #16332520;border-radius:10px;font-size:12px;line-height:1.7;font-weight:400}.pill{display:flex;align-items:center;gap:7px;border:1px solid #d5e4dc;background:#edf5f0;border-radius:30px;padding:7px 11px;white-space:nowrap;font-size:11px;color:#48765d}.dot{width:6px;height:6px;border-radius:50%;background:#4f9672}.card{background:white;border:1px solid #dfe6e1;border-radius:16px;margin-bottom:14px;padding:20px 22px;box-shadow:0 4px 18px #1b382b03}.phase-row{display:flex;align-items:center;justify-content:space-between;gap:16px}.phase{font-size:16px;font-weight:650}.percent{font-size:24px;letter-spacing:-1px;color:#31745b;font-variant-numeric:tabular-nums}.muted{font-size:12px;line-height:1.7;color:#78867e}#message{margin-top:5px;max-width:580px}.track{height:6px;background:#edf1ee;border-radius:6px;overflow:hidden;margin:16px 0 9px}.bar{height:100%;background:linear-gradient(90deg,#357e61,#82b49a);border-radius:6px;transition:width .6s}.indeterminate .bar{width:32%!important;animation:slide 1.7s infinite}@keyframes slide{from{transform:translateX(-110%)}to{transform:translateX(420%)}}.stats{display:flex;justify-content:space-between;font-size:11px;color:#839088;font-variant-numeric:tabular-nums}.steps{display:flex;justify-content:space-between;gap:12px;border-top:1px solid #edf1ee;margin-top:15px;padding-top:13px;color:#a3ada6;font-size:11px}.steps span{display:flex;align-items:center;gap:6px}.steps span:before{content:'';display:block;width:5px;height:5px;border-radius:50%;background:#dce3de}.steps .done{color:#4c8065}.steps .done:before,.steps .current:before{background:#4b9570}.steps .current{color:#264b38;font-weight:650}.warning{background:#fff5de;color:#806020;padding:10px 12px;border-radius:8px;margin-top:12px;font-size:12px;line-height:1.6;white-space:pre-wrap}.connection-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.console{font-size:12px;color:#357458;text-decoration:none;font-weight:600}.console:hover{text-decoration:underline}.credentials{display:grid;grid-template-columns:1fr 2fr;gap:20px;background:#f6f8f6;border:1px solid #ebefeb;border-radius:10px;padding:12px 14px}label{display:block;font-size:11px;color:#819087;margin-bottom:6px}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px;overflow-wrap:anywhere}.password-line{display:flex;justify-content:space-between;align-items:center;gap:10px}button{border:0;cursor:pointer;background:none;color:#468065;font-size:11px;padding:3px}.note{font-size:10px;color:#96a198;line-height:1.6;margin:8px 0 15px}.routes{display:grid;grid-template-columns:1fr 1fr;gap:20px}.route+.route{border-left:1px solid #e9eeea;padding-left:20px}.route-title{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:650;margin-bottom:6px}.route-icon{width:24px;height:24px;display:grid;place-items:center;background:#edf4ef;border-radius:7px;color:#53866b}.route p{font-size:11px;line-height:1.8;color:#7c8a80;margin:0 0 8px}.command{border:1px solid #e5ebe6;border-radius:7px;padding:8px 9px;background:#fafbf9;display:block;line-height:1.7;font-size:10px;color:#466450}.error .bar{background:#b34b51}.error .phase,.error .percent{color:#a3444a}.hidden{display:none!important}@media(max-width:560px){main{padding:20px 15px}header{margin:12px 0 17px}h1{font-size:24px}.pill{display:none}.card{padding:17px}.routes{grid-template-columns:1fr;gap:13px}.route+.route{border-left:0;border-top:1px solid #e9eeea;padding:12px 0 0}.credentials{gap:12px;grid-template-columns:1fr 2fr}.resource-row{font-size:11px}.steps{gap:5px;font-size:10px}}
</style>
<main><div class="brand">OLARES / QEMU SERVER</div><header><div><h1 id="title">Linux Server</h1><div class="resource-row"><span id="resources">—</span><details class="help"><summary id="helpButton" aria-label="Resource and storage information">?</summary><p id="helpText"></p></details></div></div><div class="pill"><span class="dot"></span>KVM</div></header>
<section class="card" id="progress"><div class="phase-row"><div class="phase" id="phase">Preparing</div><div class="percent" id="percent">—</div></div><div class="muted" id="message">Connecting to the server…</div><div class="track indeterminate" id="track"><div class="bar" id="bar"></div></div><div class="stats"><span id="bytes"></span><span id="speed"></span></div><div class="steps" id="steps"></div><div class="warning hidden" id="warning"></div></section>
<section class="card hidden" id="connection"><div class="connection-head"><div class="phase" id="connectTitle"></div><a class="console" id="console" href="/vnc.html?autoconnect=true&amp;resize=scale&amp;path=websockify"></a></div><div class="credentials"><div><label id="userLabel"></label><code id="username"></code></div><div><label id="passwordLabel"></label><div class="password-line"><code id="password">••••••••••••</code><button id="reveal" type="button" aria-pressed="false"></button></div></div></div><p class="note" id="passwordNote"></p><div class="routes"><div class="route"><div class="route-title"><span class="route-icon" aria-hidden="true">⌘</span><span id="localTitle"></span></div><p id="overlayText"></p><code class="command" id="localCommand"></code></div><div class="route"><div class="route-title"><span class="route-icon" aria-hidden="true">↗</span><span id="remoteTitle"></span></div><p id="vpnText"></p><code class="command" id="remoteCommand"></code></div></div></section></main>
<script>
const zh=navigator.language.toLowerCase().startsWith('zh');document.documentElement.lang=zh?'zh-CN':'en';const $=id=>document.getElementById(id),text=(en,cn)=>zh?cn:en;
const phases=['preparing','downloading','verifying','disk','booting','initializing','expanding','ready'];const labels=zh?['准备','下载镜像','校验镜像','准备磁盘','启动系统','初始化系统','检查磁盘扩容','服务器已就绪']:['Preparing','Downloading image','Verifying image','Preparing disk','Starting system','Initializing system','Checking disk expansion','Server ready'];let initialPassword='',shown=false;
const strings={connectTitle:['Connect to server','连接服务器'],userLabel:['Username','用户名'],passwordLabel:['Initial password','初始密码'],passwordNote:['The password set at installation. If changed with passwd, use the new password.','安装时设置的密码。如已通过 passwd 修改，请使用新密码。'],localTitle:['Same network as Olares','与 Olares 在同一网络'],remoteTitle:['Away from Olares','与 Olares 不在同一网络'],overlayText:['Enable the app in Settings → Network → Overlay gateway and use its assigned address. SSH uses port 22.','在「设置 → 网络 → Overlay 网关」启用本应用，使用分配的地址连接，默认端口为 22。'],vpnText:['Connect to Olares with LarePass VPN first. Find the device address and external SSH port in Settings → Applications → QEMU Server → Ports.','先连接 LarePass VPN，再使用 Olares 设备地址和 SSH 对外端口。可在「设置 → 应用 → QEMU Server → 端口」查看。'],helpText:['The system disk is stored in Olares App Data. Edit CPU, memory and disk in the app environment settings. Changes restart the VM; disks can only grow.','系统盘保存在 Olares App Data。CPU、内存和磁盘可在应用环境设置中修改。应用修改后会重启，磁盘仅支持扩容。'],console:['Open console ↗','打开控制台 ↗'],reveal:['Show','显示']};for(const [id,value] of Object.entries(strings))$(id).textContent=value[zh?1:0];$('helpButton').setAttribute('aria-label',text('Resource and storage information','资源与存储说明'));
$('reveal').onclick=()=>{shown=!shown;$('password').textContent=shown?initialPassword:'••••••••••••';$('reveal').textContent=shown?text('Hide','隐藏'):text('Show','显示');$('reveal').setAttribute('aria-pressed',String(shown));};
const size=n=>`${((n||0)/1073741824).toFixed(2)} GiB`;
async function poll(){try{const r=await fetch('/status.json',{cache:'no-store'});if(!r.ok)throw Error();const s=await r.json();$('title').textContent=s.title||'Linux Server';$('resources').textContent=s.cpu?`${s.cpu} vCPU · ${s.memory} GiB RAM · ${s.disk} GiB ${text('virtual disk','虚拟磁盘')}`:'—';const i=phases.indexOf(s.phase),downloading=s.phase==='downloading';$('phase').textContent=s.phase==='failed'?text('Setup needs attention','设置需要处理'):s.phase==='stopped'?text('System stopped','系统已停止'):(labels[i]||s.phase);$('message').textContent=zh?(s.message_zh||s.message):s.message;$('track').className='track'+(s.percent==null&&!s.ready&&s.phase!=='failed'?' indeterminate':'');$('bar').style.width=(s.ready?100:s.percent||0)+'%';$('percent').textContent=s.ready?'✓':downloading&&s.percent!=null?`${Number(s.percent).toFixed(1)}%`:'—';$('bytes').textContent=downloading?(s.total?`${size(s.downloaded)} / ${size(s.total)}`:size(s.downloaded)):'';$('speed').textContent=downloading&&s.speed?`${(s.speed/1048576).toFixed(1)} MiB/s`:'';$('steps').replaceChildren(...['downloading','verifying','initializing','ready'].map(p=>{const e=document.createElement('span'),j=phases.indexOf(p);e.textContent=labels[j];e.className=s.ready||j<i?'done':j===i?'current':'';return e;}));$('warning').classList.toggle('hidden',!s.warning);$('warning').textContent=s.warning||'';$('progress').classList.toggle('error',s.phase==='failed');if(s.connectable){const cr=await fetch('/connection.json',{cache:'no-store'});if(!cr.ok)throw Error();const c=await cr.json();initialPassword=c.password;$('username').textContent=c.username;$('connection').classList.remove('hidden');$('localCommand').textContent=`ssh ${c.username}@${text('<Overlay address>','<Overlay 地址>')}`;$('remoteCommand').textContent=`ssh -p ${text('<external port>','<对外端口>')} ${c.username}@${text('<Olares address>','<Olares 地址>')}`;if(shown)$('password').textContent=initialPassword;}}catch(e){$('message').textContent=text('Reconnecting… The app may be restarting.','正在重新连接，应用可能正在重启。');}setTimeout(poll,2000);}poll();
</script></html>
{{- end -}}

{{- define "qemu.runtime.nginx.conf" -}}
pid /tmp/nginx.pid;
error_log /dev/stderr;
events { worker_connections 128; }
http {
  include /etc/nginx/mime.types;
  access_log off;
  client_body_temp_path /tmp/client;
  proxy_temp_path /tmp/proxy;
  fastcgi_temp_path /tmp/fastcgi;
  uwsgi_temp_path /tmp/uwsgi;
  scgi_temp_path /tmp/scgi;
  server {
    listen 8006;
    add_header Cache-Control "no-store" always;
    root /usr/share/novnc;
    location = / { root /tmp; try_files /index.html =404; }
    location = /status.json { root /tmp; }
    location = /connection.json { root /tmp; }
    location / { try_files $uri $uri/ =404; }
    location /websockify {
      proxy_pass http://127.0.0.1:5700/;
      proxy_http_version 1.1;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_read_timeout 3600s;
      proxy_buffering off;
    }
  }
}
{{- end -}}

{{- define "qemu.runtime.start.sh" -}}
#!/usr/bin/env bash
set -Eeuo pipefail
exec python3 /opt/olares/engine.py
{{- end -}}

{{- define "qemu.runtime.vm_platform.py" -}}
"""Architecture-specific QEMU configuration; KVM remains mandatory in production."""
from pathlib import Path
import platform
import shutil


def architecture(machine=None):
    machine = (machine or platform.machine()).lower()
    aliases = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
    if machine not in aliases:
        raise ValueError('Only amd64 and arm64 hosts are supported.')
    return aliases[machine]


def check_disk_architecture(arch, image, marker):
    if marker.exists():
        if marker.read_text().strip() != arch:
            raise RuntimeError('The existing disk belongs to another CPU architecture. Use a separate installation.')
    elif image.exists():
        if arch != 'amd64':
            raise RuntimeError('Existing disk architecture is unknown. A legacy x86 disk cannot be reused on ARM.')
        marker.write_text('amd64\n')


def prepare_firmware(arch, store, firmware=Path('/usr/share/AAVMF')):
    if arch != 'arm64':
        return
    code, template = firmware / 'AAVMF_CODE.fd', firmware / 'AAVMF_VARS.fd'
    if not code.is_file() or not template.is_file():
        raise RuntimeError('ARM64 UEFI firmware is missing from the container image.')
    variables = store / 'uefi-vars.fd'
    if not variables.exists():
        shutil.copyfile(template, variables)
        variables.chmod(0o600)
    elif variables.stat().st_size != template.stat().st_size:
        raise RuntimeError('Stored ARM UEFI variables do not match the installed firmware layout.')


def command(arch, cpu, memory, image, store, firmware=Path('/usr/share/AAVMF')):
    if arch == 'amd64':
        args = ['qemu-system-x86_64', '-enable-kvm', '-machine', 'q35', '-cpu', 'host',
                '-smp', str(cpu), '-m', str(memory * 1024),
                '-drive', f'file={image},format=qcow2,if=virtio',
                '-drive', 'file=/tmp/seed.iso,format=raw,media=cdrom,readonly=on']
    elif arch == 'arm64':
        args = ['qemu-system-aarch64', '-enable-kvm', '-machine', 'virt,gic-version=host',
                '-cpu', 'host', '-smp', str(cpu), '-m', str(memory * 1024),
                '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={firmware / "AAVMF_CODE.fd"}',
                '-drive', f'if=pflash,format=raw,unit=1,file={store / "uefi-vars.fd"}',
                '-drive', f'file={image},format=qcow2,if=none,id=osdisk',
                '-device', 'virtio-blk-pci,drive=osdisk,bootindex=1',
                '-drive', 'file=/tmp/seed.iso,format=raw,if=none,id=seed,readonly=on',
                '-device', 'virtio-scsi-pci,id=seedscsi',
                '-device', 'scsi-cd,drive=seed,bus=seedscsi.0',
                '-device', 'virtio-gpu-pci', '-device', 'virtio-rng-pci', '-device', 'qemu-xhci,id=usb',
                '-device', 'usb-kbd,bus=usb.0', '-device', 'usb-tablet,bus=usb.0']
    else:
        raise ValueError('Unsupported CPU architecture.')
    return args + ['-netdev', 'user,id=net0,hostfwd=tcp:0.0.0.0:22-:22,hostfwd=tcp:0.0.0.0:2222-:22',
        '-device', 'virtio-net-pci,netdev=net0' + (',romfile=' if arch == 'arm64' else ''),
        '-vnc', '127.0.0.1:0,websocket=5700',
        '-serial', 'file:/tmp/serial.log', '-monitor', 'unix:/tmp/qemu-monitor.sock,server=on,wait=off',
        '-device', 'virtio-serial', '-chardev', 'socket,path=/tmp/qga.sock,server=on,wait=off,id=qga0',
        '-device', 'virtserialport,chardev=qga0,name=org.qemu.guest_agent.0']
{{- end -}}

// Optional release transport when this workstation cannot reach workers.dev.
// A one-off, read-only Python process in the EXISTING Railway API container
// reads the exact public installer URL over verified HTTPS. Only five JSON
// fields return over host-key-pinned SSH; no application env or files are read.
// This never reads R2 directly and never substitutes for the size/SHA-512 gate.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { execFileSync } = require("node:child_process");

const REPO = path.resolve(__dirname, "..");
const HOST = "ssh.railway.com";
const USER = "pokeapp-api-production.up.railway.app";
const MAX_BYTES = 512 * 1024 * 1024;
const INSTALLER =
  /^https:\/\/pokeapp-web\.pokeapp-v2\.workers\.dev\/launcher\/updates\/stable\/\d+\.\d+\.\d+\.exe$/;
const exact = (value, keys) =>
  value &&
  typeof value === "object" &&
  !Array.isArray(value) &&
  Object.keys(value).sort().join() === [...keys].sort().join();
const inside = (file, directory) => {
  const f = path.resolve(file).toLowerCase(),
    d = path.resolve(directory).toLowerCase();
  return f === d || f.startsWith(d + path.sep);
};
function privateFile(file, buildRoot) {
  if (
    typeof file !== "string" ||
    !path.isAbsolute(file) ||
    inside(file, REPO) ||
    (buildRoot && inside(file, buildRoot)) ||
    /^(?:\\\\|\/\/)/.test(file)
  )
    throw new Error("PUBLIC_READER_FILE_LOCATION_INVALID");
  const stat = fs.lstatSync(file);
  if (
    !stat.isFile() ||
    stat.isSymbolicLink() ||
    fs.realpathSync(file).toLowerCase() !== path.resolve(file).toLowerCase()
  )
    throw new Error("PUBLIC_READER_FILE_INVALID");
  return file;
}
function loadConfig(file, buildRoot) {
  privateFile(file, buildRoot);
  const config = JSON.parse(
    fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""),
  );
  if (
    !exact(config, [
      "provider",
      "host",
      "user",
      "identity_file",
      "known_hosts_file",
      "host_key_sha256",
    ]) ||
    config.provider !== "railway-ssh" ||
    config.host !== HOST ||
    config.user !== USER ||
    typeof config.host_key_sha256 !== "string" ||
    !/^SHA256:[A-Za-z0-9+/]{43}$/.test(config.host_key_sha256)
  )
    throw new Error("PUBLIC_READER_CONFIG_INVALID");
  privateFile(config.identity_file, buildRoot);
  privateFile(config.known_hosts_file, buildRoot);
  const hosts = fs
    .readFileSync(config.known_hosts_file, "utf8")
    .trim()
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
  const parts = hosts[0]?.split(/\s+/) || [];
  if (
    hosts.length !== 1 ||
    parts.length !== 3 ||
    parts[0] !== HOST ||
    parts[1] !== "ssh-ed25519" ||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(parts[2])
  )
    throw new Error("PUBLIC_READER_HOST_PIN_INVALID");
  const publicKey = Buffer.from(parts[2], "base64");
  if (
    publicKey.length !== 51 ||
    publicKey.readUInt32BE(0) !== 11 ||
    publicKey.subarray(4, 15).toString() !== "ssh-ed25519" ||
    publicKey.readUInt32BE(15) !== 32
  )
    throw new Error("PUBLIC_READER_HOST_PIN_INVALID");
  const fingerprint =
    "SHA256:" +
    crypto
      .createHash("sha256")
      .update(publicKey)
      .digest("base64")
      .replace(/=+$/, "");
  if (fingerprint !== config.host_key_sha256)
    throw new Error("PUBLIC_READER_HOST_PIN_MISMATCH");
  return config;
}
function parseProof(raw, url, method) {
  let proof;
  try {
    proof = JSON.parse(raw);
  } catch {
    throw new Error("PUBLIC_READER_RESPONSE_INVALID");
  }
  if (
    !exact(proof, ["url", "method", "status", "size", "sha512"]) ||
    proof.url !== url ||
    proof.method !== method ||
    !Number.isInteger(proof.status) ||
    proof.status < 100 ||
    proof.status > 599 ||
    !Number.isSafeInteger(proof.size) ||
    proof.size < 0 ||
    proof.size > MAX_BYTES ||
    (method === "HEAD" || proof.status !== 200
      ? proof.sha512 !== null
      : typeof proof.sha512 !== "string" ||
        !/^[A-Za-z0-9+/]{86}==$/.test(proof.sha512))
  )
    throw new Error("PUBLIC_READER_RESPONSE_INVALID");
  return proof;
}
function script(url, method) {
  // url and method are validated fixed-route ASCII values before interpolation.
  return `import base64,hashlib,json,urllib.request,urllib.error
url='${url}'
method='${method}'
result={'url':url,'method':method,'status':0,'size':0,'sha512':None}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs): return None
try:
 opener=urllib.request.build_opener(NoRedirect)
 with opener.open(urllib.request.Request(url,method=method,headers={'User-Agent':'PokeApp release readback'}),timeout=25) as response:
  result['status']=response.status
  if response.geturl()!=url: raise ValueError('redirected_public_url')
  if method=='HEAD':
   length=response.headers.get('content-length','0')
   result['size']=int(length) if length.isdigit() else 0
  elif response.status==200:
   digest=hashlib.sha512()
   while True:
    chunk=response.read(1024*1024)
    if not chunk: break
    result['size']+=len(chunk)
    if result['size']>${MAX_BYTES}: raise ValueError('installer_too_large')
    digest.update(chunk)
   result['sha512']=base64.b64encode(digest.digest()).decode('ascii')
except urllib.error.HTTPError as error:
 result['status']=error.code
except Exception:
 result['status']=0
 result['sha512']=None
print(json.dumps(result,separators=(',',':')))
`;
}
function createSSHReader(file, { buildRoot, execute = execFileSync } = {}) {
  const config = loadConfig(file, buildRoot);
  const reader = async (url, method) => {
    if (
      typeof url !== "string" ||
      !INSTALLER.test(url) ||
      !["HEAD", "GET"].includes(method)
    )
      throw new Error("PUBLIC_READER_REQUEST_INVALID");
    if (JSON.stringify(loadConfig(file, buildRoot)) !== JSON.stringify(config))
      throw new Error("PUBLIC_READER_CONFIG_CHANGED");
    // Never depend on the owner's SSH config, agent, default identities or
    // global known_hosts. The dedicated file and fingerprint pin one host key.
    const encoded = Buffer.from(script(url, method)).toString("base64");
    const remote = `python -c 'import base64;exec(base64.b64decode("${encoded}"))'`;
    const ssh =
      process.platform === "win32"
        ? path.join(
            process.env.SystemRoot || "C:\\Windows",
            "System32/OpenSSH/ssh.exe",
          )
        : "ssh";
    let raw;
    try {
      raw = execute(
        ssh,
        [
          "-F",
          process.platform === "win32" ? "NUL" : "/dev/null",
          "-T",
          "-o",
          "BatchMode=yes",
          "-o",
          "IdentitiesOnly=yes",
          "-o",
          "ConnectTimeout=15",
          "-o",
          "ServerAliveInterval=10",
          "-o",
          "ServerAliveCountMax=3",
          "-o",
          "StrictHostKeyChecking=yes",
          "-o",
          "HostKeyAlgorithms=ssh-ed25519",
          "-o",
          "GlobalKnownHostsFile=" +
            (process.platform === "win32" ? "NUL" : "/dev/null"),
          "-o",
          "UserKnownHostsFile=" + config.known_hosts_file,
          "-o",
          "ClearAllForwardings=yes",
          "-o",
          "ForwardAgent=no",
          "-o",
          "PermitLocalCommand=no",
          "-o",
          "LogLevel=ERROR",
          "-i",
          config.identity_file,
          `${USER}@${HOST}`,
          remote,
        ],
        {
          encoding: "utf8",
          timeout: 60000,
          maxBuffer: 16384,
          windowsHide: true,
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
    } catch {
      throw new Error("PUBLIC_READER_SSH_FAILED");
    }
    return parseProof(raw, url, method);
  };
  reader.transport = Object.freeze({
    provider: config.provider,
    host: HOST,
    user: USER,
    host_key_sha256: config.host_key_sha256,
  });
  return reader;
}
module.exports = { createSSHReader, loadConfig, parseProof };

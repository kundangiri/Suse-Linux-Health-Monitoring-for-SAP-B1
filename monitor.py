from flask import Flask, request, render_template_string, redirect, url_for, session
from pam import pam
import psutil, socket, datetime, netifaces
import subprocess

app = Flask(__name__)
app.secret_key = "your-secret-key"  # Change to a strong secret for production

auth = pam()

def get_ip():
    interfaces = netifaces.interfaces()
    for iface in interfaces:
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                if ip != "127.0.0.1":
                    return ip
    return "No IP Found"

def check_partition_usage(path):
    try:
        usage = psutil.disk_usage(path).percent
        return usage
    except Exception:
        return None

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if auth.authenticate(username, password):
            session['username'] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template_string(LOGIN_PAGE, error="Invalid credentials")

    return render_template_string(LOGIN_PAGE, error=None)

@app.route("/dashboard")
def dashboard():
    if 'username' not in session:
        return redirect(url_for("login"))

    disk_usages = {
        "/": check_partition_usage('/'),
        "/hana/shared": check_partition_usage('/hana/shared'),
        "/hana/data": check_partition_usage('/hana/data'),
        "/hana/log": check_partition_usage('/hana/log'),
        "/usr/sap": check_partition_usage('/usr/sap')
    }
    # Clean None to 0 or "N/A"
    for k, v in disk_usages.items():
        if v is None:
            disk_usages[k] = 0

    health = {
        "hostname": socket.gethostname(),
        "ip": get_ip(),
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk_usages": disk_usages,
        "uptime": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
    }

    return render_template_string(DASHBOARD_PAGE, user=session['username'], health=health, console_output=None)

@app.route("/console", methods=["GET", "POST"])
def console():
    if 'username' not in session:
        return redirect(url_for("login"))

    output = ""
    error = None

    if request.method == "POST":
        command = request.form.get("command", "").strip()
        # Whitelist allowed commands
        allowed_commands = ['ls', 'df', 'uptime', 'free', 'ps']

        # To allow commands like "ps aux" or "ls -l" safely,
        # we split and check the first part only
        cmd_parts = command.split()
        if len(cmd_parts) == 0 or cmd_parts[0] not in allowed_commands:
            error = "Command not allowed."
        else:
            try:
                # Run the command with shell=False for safety
                # pass the split command as list for subprocess
                result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=5)
                output = result.stdout + (result.stderr if result.stderr else "")
            except Exception as e:
                error = f"Failed to run command: {e}"

    return render_template_string(CONSOLE_PAGE, output=output, error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


LOGIN_PAGE="""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Login - SAP B1 Monitor</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
<style>
  html, body {
    height: 100%;
    margin: 0;
    background-color: #f8f9fa;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  }
  .container-fluid {
    height: 100vh;
  }
  .row-full {
    height: 100%;
  }

  /* Left side: background image + logos + text */
  .info-side {
    position: relative;
    background: url('https://images.unsplash.com/photo-1519389950473-47ba0277781c?auto=format&fit=crop&w=800&q=80') no-repeat center center;
    background-size: cover;
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 3rem 2rem;
    text-align: center;
  }
  /* overlay to darken the background for readability */
  .info-side::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 0;
  }
  .info-content {
    position: relative;
    z-index: 1;
    max-width: 350px;
  }
  .info-content img {
    max-width: 140px;
    margin: 10px auto;
    display: block;
  }
  .info-content h1 {
    font-weight: 700;
    font-size: 2.2rem;
    margin: 1rem 0 0.5rem;
  }
  .info-content p {
    font-size: 1.1rem;
    line-height: 1.4;
    margin-bottom: 2rem;
  }

  /* Right side: login form */
  .login-side {
    background-color: #ffffff;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 3rem 2rem;
  }
  .login-box {
    max-width: 400px;
    width: 100%;
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.1);
    border-radius: 10px;
    padding: 2.5rem;
  }
  h2 {
    margin-bottom: 1.5rem;
    font-weight: 700;
    color: #212529;
    text-align: center;
  }
  .form-control {
    border-radius: 6px;
    border: 1.5px solid #ced4da;
    padding: 0.75rem 1rem;
    font-size: 1rem;
  }
  .form-control:focus {
    border-color: #0d6efd;
    box-shadow: 0 0 0 0.25rem rgb(13 110 253 / 0.25);
  }
  .btn-primary {
    background-color: #0d6efd;
    border: none;
    font-weight: 600;
    padding: 0.75rem;
    border-radius: 6px;
    font-size: 1.1rem;
  }
  .btn-primary:hover {
    background-color: #084bcc;
  }
  .alert {
    font-size: 0.9rem;
  }

  /* Responsive */
  @media (max-width: 767.98px) {
    .info-side {
      display: none;
    }
    .login-side {
      padding: 3rem 1rem;
    }
  }
.info-content img.company-logo {
  background: white;
  padding: 8px 16px;
  border-radius: 8px;
  max-width: 160px;
  margin: 10px auto 20px;
  display: block;
}
</style>
</head>
<body>

<div class="container-fluid">
  <div class="row row-full gx-0">
    <!-- Left side with image, logos, info -->
    <div class="col-md-6 info-side">
      
<div class="info-content">
        <!-- BizHub logo 
        <img
  src="https://bizhub.com.np/wp-content/uploads/2023/08/BizHub-logo-300x160.jpeg"
  alt="BizHub Logo"
  class="company-logo"
/> -->
       <!-- SAP logo (official) -->
        <img src="https://upload.wikimedia.org/wikipedia/commons/5/59/SAP_2011_logo.svg" alt="SAP Logo" style="max-width: 120px; margin: 1rem auto;" />
        <h1>Welcome to BizHub SAP B1 Monitor</h1>
        <p>Your trusted partner for SAP Business One server monitoring and management solutions. Efficient, reliable, and secure.</p>
      </div>
    </div>

    <!-- Right side with login form -->
    <div class="col-md-6 login-side">
      <div class="login-box">
        <h2>SAP B1 Monitor Login</h2>
        {% if error %}
        <div class="alert alert-danger" role="alert">{{ error }}</div>
        {% endif %}
        <form method="POST" novalidate>
          <div class="mb-4">
            <label for="username" class="form-label">Username</label>
            <input
              type="text"
              class="form-control"
              id="username"
              name="username"
              placeholder="Enter username"
              required
              autofocus
            />
          </div>
          <div class="mb-4">
            <label for="password" class="form-label">Password</label>
            <input
              type="password"
              class="form-control"
              id="password"
              name="password"
              placeholder="Enter password"
              required
            />
          </div>
          <button type="submit" class="btn btn-primary w-100">Login</button>
        </form>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
DASHBOARD_PAGE="""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SAP B1 Server Health Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
<style>
  body {
    background-color: #f8f9fa;  /* light gray background */
    color: #212529;             /* Bootstrap's default body color */
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    font-weight: 400;
    text-rendering: optimizeLegibility;
  }
  .navbar, .card {
    background-color: #ffffff; /* white background for navbar and cards */
    box-shadow: 0 0 10px rgba(0,0,0,0.1);
  }
  h2 {
    font-weight: 600;
    color: #0d6efd;  /* Bootstrap primary blue */
  }
  ul.list-unstyled li {
    padding: 6px 0;
    font-size: 1.05rem;
  }
  pre {
    background: #e9ecef; /* light gray, matching Bootstrap */
    color: #212529;
    padding: 10px;
    max-height: 200px;
    overflow: auto;
    border-radius: 5px;
    font-family: monospace;
    font-weight: 500;
  }
  a.nav-link {
    color: #0d6efd;
    font-weight: 500;
  }
  a.nav-link:hover {
    color: #0a58ca;
    text-decoration: underline;
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-light px-3 shadow-sm">
  <a class="navbar-brand fw-bold" href="/dashboard">SAP B1 Monitor</a>
  <div class="collapse navbar-collapse">
    <ul class="navbar-nav ms-auto">
      <li class="nav-item"><a class="nav-link" href="/console">Console</a></li>
      <li class="nav-item"><a class="nav-link" href="/logout">Logout</a></li>
    </ul>
  </div>
</nav>

<div class="container py-4">
  <div class="card mb-4 p-4">
    <h2>Server Info</h2>
    <p><strong>Hostname:</strong> {{ health.hostname }}</p>
    <p><strong>IP Address:</strong> {{ health.ip }}</p>
    <p><strong>Uptime Since:</strong> {{ health.uptime }}</p>
  </div>

  <div class="card mb-4 p-4">
    <h2>CPU & Memory Usage</h2>
    <canvas id="cpuChart" height="100"></canvas>
    <canvas id="memChart" height="100" class="mt-3"></canvas>
  </div>

  <div class="card mb-4 p-4">
    <h2>Disk Usage</h2>
    <ul class="list-unstyled">
      {% for part, usage in health.disk_usages.items() %}
      <li><strong>{{ part }}:</strong> {{ usage }}%</li>
      {% endfor %}
    </ul>
    <canvas id="diskChart" height="150"></canvas>
  </div>
</div>

<script>
const cpuUsage = {{ health.cpu }};
const memUsage = {{ health.memory }};
const diskLabels = {{ health.disk_usages.keys() | list | tojson }};
const diskData = {{ health.disk_usages.values() | list | tojson }};

function getColor(value) {
  if (value > 90) return 'rgba(220, 53, 69, 0.8)';  // red
  if (value > 70) return 'rgba(255, 193, 7, 0.8)';  // yellow
  return 'rgba(25, 135, 84, 0.8)';                  // green
}

const ctxCpu = document.getElementById('cpuChart').getContext('2d');
new Chart(ctxCpu, {
  type: 'bar',
  data: {
    labels: ['CPU Usage'],
    datasets: [{ label: 'CPU %', data: [cpuUsage], backgroundColor: getColor(cpuUsage) }]
  },
  options: { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } }
});

const ctxMem = document.getElementById('memChart').getContext('2d');
new Chart(ctxMem, {
  type: 'bar',
  data: {
    labels: ['Memory Usage'],
    datasets: [{ label: 'Memory %', data: [memUsage], backgroundColor: getColor(memUsage) }]
  },
  options: { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } }
});

const ctxDisk = document.getElementById('diskChart').getContext('2d');
new Chart(ctxDisk, {
  type: 'bar',
  data: {
    labels: diskLabels,
    datasets: [{ label: 'Disk Usage %', data: diskData, backgroundColor: diskData.map(getColor) }]
  },
  options: { scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } }
});
</script>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>

"""
CONSOLE_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Web Console - SAP B1 Monitor</title>
<style>
body { font-family: monospace; background: #111; color: #0f0; padding: 20px; }
input[type=text] { width: 80%; padding: 8px; border-radius: 4px; border: none; margin-right: 8px; background: #222; color: #0f0; }
input[type=submit] { padding: 8px 16px; border-radius: 4px; border: none; background: #5cb85c; color: #000; font-weight: bold; cursor: pointer; }
input[type=submit]:hover { background: #4cae4c; }
.error { color: #f66; }
pre { white-space: pre-wrap; background: #000; padding: 15px; max-height: 300px; overflow-y: auto; border-radius: 5px; }
a { color: #ccc; text-decoration: none; }
a:hover { color: #5cb85c; }
</style>
</head>
<body>
<h2>Web Console</h2>
{% if error %}
<p class="error">{{ error }}</p>
{% endif %}
<form method="POST">
    <input type="text" name="command" placeholder="Enter command (ls, df, uptime, free, ps)" required autofocus>
    <input type="submit" value="Run">
</form>
{% if output %}
<pre>{{ output }}</pre>
{% endif %}
<p><a href="{{ url_for('dashboard') }}">Back to Dashboard</a></p>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Blood Bank - Admin Login</title>

    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        body {
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
            background: linear-gradient(135deg, #8b0015, #ef5350);
        }

        .login-box {
            width: 100%;
            max-width: 420px;
            padding: 38px;
            text-align: center;
            background: white;
            border-radius: 16px;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.22);
        }

        h1 {
            margin-bottom: 12px;
            color: #b51224;
            font-size: 28px;
        }

        .subtitle {
            margin-bottom: 24px;
            color: #666;
            line-height: 1.5;
        }

        h2 {
            margin-bottom: 12px;
            color: #333;
        }

        .demo-login {
            margin-bottom: 14px;
            color: #555;
            font-size: 14px;
        }

        .message {
            margin: 12px 0;
            padding: 11px;
            color: #9b1020;
            background: #ffe8ea;
            border-radius: 6px;
        }

        input {
            width: 100%;
            margin: 9px 0;
            padding: 13px;
            border: 1px solid #ccc;
            border-radius: 7px;
            font-size: 16px;
        }

        input:focus {
            border-color: #b51224;
            outline: 2px solid rgba(181, 18, 36, 0.15);
        }

        button {
            width: 100%;
            margin-top: 12px;
            padding: 13px;
            color: white;
            background: #b51224;
            border: 0;
            border-radius: 7px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }

        button:hover {
            background: #870018;
        }

        .register-link {
            display: inline-block;
            margin-top: 20px;
            color: #b51224;
            font-weight: bold;
            text-decoration: none;
        }

        .register-link:hover {
            text-decoration: underline;
        }

        @media (max-width: 480px) {
            .login-box {
                padding: 28px 22px;
            }

            h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <main class="login-box">
        <h1>🩸 Smart Blood Bank</h1>
        <p class="subtitle">Management &amp; Intelligent Donor Matching System</p>

        <h2>Admin Login</h2>
        <p class="demo-login">Demo login: <strong>admin</strong> / <strong>admin123</strong></p>

        {% for message in get_flashed_messages() %}
            <p class="message">{{ message }}</p>
        {% endfor %}

        <form action="{{ url_for('login') }}" method="POST">
            <input
                type="text"
                name="username"
                placeholder="Enter Username"
                autocomplete="username"
                required
            >

            <input
                type="password"
                name="password"
                placeholder="Enter Password"
                autocomplete="current-password"
                required
            >

            <button type="submit">Login</button>
        </form>

        <a class="register-link" href="{{ url_for('register_donor') }}">
            Register as a Blood Donor
        </a>
    </main>
</body>
</html>